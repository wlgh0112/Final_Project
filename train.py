import os, shutil, sys, getpass
from pathlib import Path
import yaml

WORKSPACE, PROJECT, VERSION = "object-detection-mb16y", "old-hand-gestures-3", 1
EPOCHS, IMGSZ, BATCH = 2, 640, 32
TARGET = ["right", "left", "fist", "palm"]   # 0:오른쪽 1:왼쪽 2:주먹 3:손펴기
ALIASES = {"right": "right", "left": "left", "fist": "fist", "closed_fist": "fist",
           "palm": "palm", "open_palm": "palm"}
DROP = {"forward", "up"}
OUT = Path("hand4")


def download():
    from roboflow import Roboflow
    key = os.environ.get("ROBOFLOW_API_KEY") or getpass.getpass("Roboflow API key: ")
    rf = Roboflow(api_key=key)
    ds = rf.workspace(WORKSPACE).project(PROJECT).version(VERSION).download("yolov8")
    return Path(ds.location)


def remap(src: Path, dst: Path):
    cfg = yaml.safe_load((src / "data.yaml").read_text(encoding="utf-8"))
    names = cfg["names"]
    if isinstance(names, dict):
        names = [names[k] for k in sorted(names, key=int)]
    print("원본 클래스:", dict(enumerate(names)))

    id_map, unknown = {}, []
    for i, n in enumerate(names):
        k = n.strip().lower()
        if k in DROP:
            continue
        if k in ALIASES:
            id_map[i] = TARGET.index(ALIASES[k])
        else:
            unknown.append(n)
    if unknown:
        sys.exit(f"매핑되지 않은 클래스: {unknown} -> ALIASES/DROP에 추가하세요.")
    missing = [t for i, t in enumerate(TARGET) if i not in id_map.values()]
    if missing:
        sys.exit(f"원본에 없는 클래스: {missing}")

    if dst.exists():
        shutil.rmtree(dst)
    stats = {}
    for sdir, out in {"train": "train", "valid": "val", "val": "val", "test": "test"}.items():
        img_dir, lbl_dir = src / sdir / "images", src / sdir / "labels"
        if not img_dir.exists():
            continue
        (dst / "images" / out).mkdir(parents=True, exist_ok=True)
        (dst / "labels" / out).mkdir(parents=True, exist_ok=True)
        kept = dropped = 0
        for img in img_dir.iterdir():
            if not img.is_file():
                continue
            lbl = lbl_dir / (img.stem + ".txt")
            lines = []
            if lbl.exists():
                for ln in lbl.read_text().splitlines():
                    p = ln.split()
                    if len(p) >= 5 and int(float(p[0])) in id_map:
                        lines.append(" ".join([str(id_map[int(float(p[0]))])] + p[1:]))
            if not lines:
                dropped += 1
                continue
            shutil.copy2(img, dst / "images" / out / img.name)
            (dst / "labels" / out / (img.stem + ".txt")).write_text("\n".join(lines))
            kept += 1
        stats[out] = (kept, dropped)

    data = {"path": str(dst.resolve()), "train": "images/train", "val": "images/val",
            "names": dict(enumerate(TARGET))}
    if "test" in stats:
        data["test"] = "images/test"
    (dst / "data.yaml").write_text(yaml.safe_dump(data, sort_keys=False))

    cnt = {n: 0 for n in TARGET}
    for f in (dst / "labels").rglob("*.txt"):
        for ln in f.read_text().splitlines():
            if ln.strip():
                cnt[TARGET[int(ln.split()[0])]] += 1
    print("결과 (유지, 버림):", stats)
    print("클래스별 박스 수:", cnt)
    return dst / "data.yaml"


if __name__ == "__main__":
    src = download()
    data_yaml = remap(src, OUT)

    from ultralytics import YOLO
    model = YOLO("yolo26n.pt")
    model.train(
        data=str(data_yaml),
        epochs=EPOCHS,
        imgsz=IMGSZ,
        batch=BATCH,
        fliplr=0.0,
        flipud=0.0,
        patience=30,
    )
    print(model.val())