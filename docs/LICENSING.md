# Licensing (TODO: open decision)

**Status: no license chosen.** This page records the facts and the options so the maintainers can decide. It is not legal advice; get counsel before publishing a release.

## Facts found in the repository

- There is no `LICENSE` file at the repository root.
- The ROS packages declare Apache-2.0: `aims_ws/src/csi` (`Apache License 2.0` in `package.xml` and `setup.py`), `aims_ws/src/custom_interfaces`, and all six vision packages (`Apache-2.0` in `package.xml`; `moving`, `pose_estimation` and `there_is_person` also in `setup.py`, with an Apache header). I did not check the web server, scripts or `utils/`.
- `pose_estimation` uses `ultralytics` (pinned in `requirements/vision-cpu.in`, `ultralytics==8.4.177`). Ultralytics is released under AGPL-3.0 and also sold under an Enterprise license (to verify on the current Ultralytics license page).
- The YOLOv8 weights `models/vision/yolov8n-pose.pt` come from Ultralytics and are covered by the same AGPL-3.0 terms (to verify).
- Maintainers named in `package.xml`: Victor Hugo (`csi`, `custom_interfaces`) and Lucas Reis (vision packages). Vision code was imported from MyCareBed, so its contributors hold copyright too.

## What the licenses mean (short, to verify with counsel)

- **Apache-2.0** is permissive: anyone may use, modify and redistribute the code, including in closed products, if they keep the notices and state changes. It includes a patent grant.
- **AGPL-3.0** is strong copyleft. If you distribute a work that contains or is derived from AGPL code, the whole combined work must be offered under AGPL-3.0 with its source. Section 13 adds a network clause: if you modify the program and users interact with it over a network, you must offer those users the source of your modified version, even without distributing copies.
- **Is the vision subsystem a "combined work" with the rest?** Uncertain. The vision code runs in its own image (`docker/vision/Dockerfile`, Compose profile `vision`) and talks to the core only through ROS topics (`/estimation_points`, `/there_is_person`, `/is_moving`, `/vision_image`). Separate processes exchanging messages are often treated as separate works, but `pose_estimation` itself imports `ultralytics`, so at least that package is a combined work. Needs counsel.
- The weights file is AGPL material that ships in this repository, so redistributing the repository redistributes it under AGPL terms.
- Changing or choosing a license needs the consent of every copyright holder of the affected code, not only the current maintainers.

## Options

| Option | Pros | Cons |
|---|---|---|
| (a) License the whole repo AGPL-3.0 | Consistent with Ultralytics; no ambiguity about the vision part | Hard for companies and hospitals to adopt; changes the declared Apache-2.0 packages (needs all authors' consent); network clause reaches anyone running a modified dashboard stack |
| (b) Apache-2.0 for the repo, vision subsystem documented as an AGPL-3.0 component | Keeps the declared license; clear boundary if the vision image is kept separate | Boundary is a legal judgement; `pose_estimation` and the weights must be clearly marked AGPL; downstream users inherit AGPL duties when they ship the vision image |
| (c) Ultralytics Enterprise license | Removes AGPL duties for ultralytics and weights | Paid; the license is held by whoever buys it, so it may not cover forks or the public repo |
| (d) Replace ultralytics/YOLO with a permissive pose model | Clean Apache-2.0 repo | Engineering work: new `pose_estimation`, new keypoint layout for `there_is_person` and `moving` (rule thresholds were tuned for YOLOv8 keypoints), retest |

Candidates for (d), licenses to verify before use: MediaPipe Pose (Apache-2.0, to verify), RTMPose / MMPose (Apache-2.0, to verify), plus the license of the specific weights, which can differ from the code license.

## Checklist

| Decision | Who decides |
|---|---|
| Choose option (a), (b), (c) or (d) | Project maintainers, with the institution |
| Confirm the legal reading of "combined work" for the separate vision image | Legal counsel |
| Collect consent from all copyright holders (package.xml authors, MyCareBed contributors) | Maintainers |
| Add a `LICENSE` file and make `package.xml` / `setup.py` / headers match | Maintainers |
| Document third-party licenses (ultralytics, weights, other pinned dependencies in `requirements/*.lock`) | Maintainers |
| If (b): mark `pose_estimation` and the weights as AGPL-3.0 and say so in `aims_ws/src/vision/README.md` and the README | Maintainers |
| If (c): buy the license and record its scope | Institution |
| If (d): pick the model, check its code and weights license, port and retest the vision nodes | Maintainers |
| Update the README "License" section | Maintainers |
