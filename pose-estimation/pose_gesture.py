"""
손 키포인트(포즈 추정) 기반 제스처 인식 파이프라인

흐름:
  1) train-pose : YOLO-pose를 Ultralytics Hand Keypoints 데이터셋(21개 키포인트)으로 학습
  2) extract    : hand4 데이터셋(라벨 있는 이미지)에서 키포인트를 뽑아 특징 벡터로 저장
  3) train-clf  : 키포인트 특징 -> 제스처 분류기(MLP) 학습, 검증 결과 출력
  4) infer      : 웹캠에서 [포즈 모델 -> 분류기 -> 연속 프레임 안정화] 실행

사용 예:
  set KMP_DUPLICATE_LIB_OK=TRUE
  python pose_gesture.py train-pose --epochs 100
  python pose_gesture.py extract --root hand4 --pose runs/pose/train/weights/best.pt
  python pose_gesture.py train-clf --npz hand_feats.npz --out gesture_clf.joblib
  python pose_gesture.py infer --pose runs/pose/train/weights/best.pt --clf gesture_clf.joblib
"""
import argparse
from collections import Counter, deque
from pathlib import Path

import numpy as np
import yaml

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
TIPS = [4, 8, 12, 16, 20]   # 엄지~새끼 손끝 (MediaPipe/Ultralytics 21점 규약)


# ───────────────────────── 특징 추출 ─────────────────────────
def kpts_to_feat(k):
    """(21, 2) 픽셀 좌표 -> 특징 벡터.
    손목 기준 이동 + 손 크기로 스케일 정규화. 회전은 일부러 정규화하지 않음
    (left/right 같은 '방향' 제스처를 구분해야 하므로)."""
    k = np.asarray(k, dtype=np.float32)
    rel = k - k[0]
    scale = max(np.linalg.norm(k[9] - k[0]),      # 손목 -> 중지 뿌리
                np.linalg.norm(k[5] - k[17])) + 1e-6   # 검지 뿌리 <-> 새끼 뿌리(손바닥 폭)
    rel = rel / scale
    tips = np.linalg.norm(rel[TIPS], axis=1)      # 손끝-손목 거리 (손가락이 펴졌는지)
    return np.concatenate([rel[1:].ravel(), tips]).astype(np.float32)


def iou_xyxy(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def yolo_to_xyxy(cx, cy, w, h, W, H):
    return ((cx - w / 2) * W, (cy - h / 2) * H, (cx + w / 2) * W, (cy + h / 2) * H)


def load_names(root: Path):
    cfg = yaml.safe_load((root / "data.yaml").read_text(encoding="utf-8"))
    n = cfg["names"]
    return [n[k] for k in sorted(n, key=int)] if isinstance(n, dict) else list(n)


def balance(X, y, seed=0):
    """소수 클래스를 복제해서 클래스 수를 맞춤 (train 전용)."""
    rng = np.random.default_rng(seed)
    classes, counts = np.unique(y, return_counts=True)
    target = counts.max()
    idx = []
    for c in classes:
        ci = np.where(y == c)[0]
        idx.append(ci)
        if len(ci) < target:
            idx.append(rng.choice(ci, target - len(ci), replace=True))
    idx = np.concatenate(idx)
    return X[idx], y[idx]


def pick_device(arg="auto"):
    """GPU가 있으면 GPU(0), 없으면 CPU. 어떤 장치를 쓰는지 항상 출력."""
    if arg not in (None, "auto"):
        print(f"장치: {arg} (사용자 지정)")
        return arg
    import torch
    if torch.cuda.is_available():
        print(f"장치: GPU 0 ({torch.cuda.get_device_name(0)})")
        return 0
    print("⚠ GPU를 찾지 못해 CPU로 실행합니다. torch가 CPU 전용 빌드일 수 있습니다.")
    print('  확인: python -c "import torch; print(torch.__version__, torch.cuda.is_available())"')
    return "cpu"


# ───────────────────────── 1) 포즈 모델 학습 ─────────────────────────
def cmd_train_pose(a):
    from ultralytics import YOLO
    dev = pick_device(a.device)
    print(f"베이스 모델: {a.base}")
    model = YOLO(a.base)   # 사전학습 포즈 모델에서 전이학습
    kw = dict(data="hand-keypoints.yaml", epochs=a.epochs, imgsz=a.imgsz, batch=a.batch, device=dev,
              patience=a.patience,          # 개선이 N에폭 없으면 조기 종료
              workers=a.workers,            # 데이터 로딩 프로세스 수
              fraction=a.fraction,          # 학습 데이터 사용 비율 (1.0=전부)
              plots=not a.no_plots)
    if a.cache != "none":
        kw["cache"] = a.cache             # ram | disk : 이미지 디코딩/리사이즈 반복 제거
    if a.project:
        kw["project"] = a.project         # 예: 코랩에서 /content/drive/MyDrive/hand_runs (세션 끊겨도 보존)
    if a.name:
        kw["name"] = a.name
    if a.no_val:
        kw["val"] = False                 # 에폭마다 검증 생략 (마지막에만) -> 최고 모델 선택은 안 됨
    print("학습 설정:", kw)
    model.train(**kw)


# ───────────────────────── 2) 키포인트 특징 추출 ─────────────────────────
def cmd_extract(a):
    from ultralytics import YOLO
    root = Path(a.root)
    names = load_names(root)
    dev = pick_device(a.device)
    model = YOLO(a.pose)
    X, y, split = [], [], []
    tot, hit = Counter(), Counter()

    for sp in ("train", "val", "test"):
        img_dir, lbl_dir = root / "images" / sp, root / "labels" / sp
        if not img_dir.exists():
            continue
        paths = sorted(str(p) for p in img_dir.iterdir() if p.suffix.lower() in IMG_EXTS)
        for r in model.predict(paths, stream=True, verbose=False, imgsz=a.imgsz, conf=a.conf, device=dev):
            lbl = lbl_dir / (Path(r.path).stem + ".txt")
            if not lbl.exists():
                continue
            H, W = r.orig_shape
            has_det = r.boxes is not None and len(r.boxes) > 0 and r.keypoints is not None
            det = r.boxes.xyxy.cpu().numpy() if has_det else None
            kp = r.keypoints.xy.cpu().numpy() if has_det else None
            for ln in lbl.read_text().splitlines():
                p = ln.split()
                if len(p) < 5:
                    continue
                c = int(float(p[0]))
                gt = yolo_to_xyxy(*map(float, p[1:5]), W, H)
                tot[names[c]] += 1
                if not has_det:
                    continue
                ious = [iou_xyxy(gt, d) for d in det]
                j = int(np.argmax(ious))
                if ious[j] < a.iou:
                    continue
                X.append(kpts_to_feat(kp[j]))
                y.append(c)
                split.append(sp)
                hit[names[c]] += 1
        print(f"[{sp}] 처리 완료")

    print("\n클래스별 키포인트 추출 성공률 (성공/전체):")
    for n in names:
        print(f"  {n:<8} {hit[n]:>6}/{tot[n]:<6} ({hit[n] / max(tot[n], 1):.0%})")
    np.savez(a.out, X=np.array(X), y=np.array(y), split=np.array(split), names=np.array(names))
    print(f"저장: {a.out}  (샘플 {len(X)}개)")


# ───────────────────────── 3) 분류기 학습 ─────────────────────────
def cmd_train_clf(a):
    import joblib
    from sklearn.metrics import classification_report, confusion_matrix
    from sklearn.neural_network import MLPClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    d = np.load(a.npz)
    X, y, split, names = d["X"], d["y"], d["split"], [str(n) for n in d["names"]]
    tr, va = split == "train", split == "val"
    Xtr, ytr = balance(X[tr], y[tr])
    clf = make_pipeline(StandardScaler(),
                        MLPClassifier(hidden_layer_sizes=(128, 64), max_iter=600,
                                      early_stopping=True, random_state=0))
    clf.fit(Xtr, ytr)
    if va.any():
        pred = clf.predict(X[va])
        labels = list(range(len(names)))
        print(classification_report(y[va], pred, labels=labels, target_names=names, zero_division=0))
        print("혼동 행렬 (행=정답, 열=예측):")
        print(confusion_matrix(y[va], pred, labels=labels))
    else:
        print("val 샘플이 없어 검증을 건너뜀")
    joblib.dump({"clf": clf, "names": names}, a.out)
    print(f"저장: {a.out}")


# ───────────────────────── 4) 웹캠 추론 ─────────────────────────
def cmd_infer(a):
    import cv2
    import joblib
    from ultralytics import YOLO

    pack = joblib.load(a.clf)
    clf, names = pack["clf"], pack["names"]
    dev = pick_device(a.device)
    pose = YOLO(a.pose)
    hist = deque(maxlen=a.stable)
    cap = cv2.VideoCapture(a.cam)
    while cap.isOpened():
        ok, frame = cap.read()
        if not ok:
            break
        if a.mirror:
            frame = cv2.flip(frame, 1)   # 학습 이미지와 같은 좌우 기준이어야 함
        res = pose.predict(frame, verbose=False, imgsz=a.imgsz, conf=a.conf, device=dev)[0]
        label, prob = None, 0.0
        if res.boxes is not None and len(res.boxes) > 0 and res.keypoints is not None:
            i = int(res.boxes.conf.argmax())
            kp = res.keypoints.xy[i].cpu().numpy()
            x1, y1, x2, y2 = map(int, res.boxes.xyxy[i].tolist())
            proba = clf.predict_proba([kpts_to_feat(kp)])[0]
            j = int(proba.argmax())
            label, prob = (names[j], float(proba[j])) if proba[j] >= a.thr else ("unknown", float(proba[j]))
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            for x, y in kp:
                cv2.circle(frame, (int(x), int(y)), 3, (0, 0, 255), -1)
            cv2.putText(frame, f"{label} {prob:.2f}", (x1, max(y1 - 8, 12)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        hist.append(label)
        if len(hist) == hist.maxlen and len(set(hist)) == 1 and hist[0] not in (None, "unknown"):
            cv2.putText(frame, f"ACTION: {hist[0]}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 200, 255), 2)
        cv2.imshow("gesture", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()


# ───────────────────────── CLI ─────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("train-pose")
    p.add_argument("--base", default="yolo26n-pose.pt")
    p.add_argument("--epochs", type=int, default=100)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--batch", type=int, default=32, help="-1이면 GPU 메모리에 맞춰 자동 결정")
    p.add_argument("--device", default="auto", help="auto(GPU 우선) | 0 | cpu")
    p.add_argument("--patience", type=int, default=15, help="조기 종료 기준(에폭)")
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--cache", choices=["none", "ram", "disk"], default="none")
    p.add_argument("--fraction", type=float, default=1.0, help="학습 데이터 사용 비율 0~1")
    p.add_argument("--no-val", action="store_true", help="에폭마다 검증 생략")
    p.add_argument("--no-plots", action="store_true", help="학습 중 그래프/샘플 이미지 저장 생략")
    p.add_argument("--project", default=None, help="결과 저장 폴더 (미지정 시 runs/pose)")
    p.add_argument("--name", default=None, help="실행 이름 (미지정 시 train, train2, ...)")
    p.set_defaults(fn=cmd_train_pose)

    p = sub.add_parser("extract")
    p.add_argument("--root", default="hand4")
    p.add_argument("--pose", required=True)
    p.add_argument("--out", default="hand_feats.npz")
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--conf", type=float, default=0.25)
    p.add_argument("--iou", type=float, default=0.3, help="GT 박스와 포즈 검출 박스 매칭 최소 IoU")
    p.add_argument("--device", default="auto", help="auto(GPU 우선) | 0 | cpu")
    p.set_defaults(fn=cmd_extract)

    p = sub.add_parser("train-clf")
    p.add_argument("--npz", default="hand_feats.npz")
    p.add_argument("--out", default="gesture_clf.joblib")
    p.set_defaults(fn=cmd_train_clf)

    p = sub.add_parser("infer")
    p.add_argument("--pose", required=True)
    p.add_argument("--clf", default="gesture_clf.joblib")
    p.add_argument("--cam", type=int, default=0)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--conf", type=float, default=0.4)
    p.add_argument("--thr", type=float, default=0.6, help="분류 확률이 이보다 낮으면 unknown")
    p.add_argument("--stable", type=int, default=8, help="같은 결과가 연속 N프레임이어야 ACTION 표시")
    p.add_argument("--mirror", action="store_true", help="셀카처럼 좌우 반전해서 입력")
    p.add_argument("--device", default="auto", help="auto(GPU 우선) | 0 | cpu")
    p.set_defaults(fn=cmd_infer)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
