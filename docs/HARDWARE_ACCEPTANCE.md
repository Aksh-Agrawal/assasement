# Prototype Hardware Acceptance

Status: all physical checks are pending execution on the Raspberry Pi prototype.

## Board and OS

- [ ] Raspberry Pi boots reliably.
- [ ] SSH works using the intended development account/key.
- [ ] Exact Raspberry Pi model recorded.
- [ ] Raspberry Pi OS image/version recorded.
- [ ] Kernel version recorded.
- [ ] 32-bit or 64-bit architecture recorded.
- [ ] Boot time recorded.
- [ ] RAM and storage baseline recorded.
- [ ] Phases 0–5 application smoke test runs on the Pi.

## Display and touch

- [ ] Display is detected by the DRM stack.
- [ ] Display produces a stable image.
- [ ] Native and active resolutions verified rather than assumed.
- [ ] Refresh rate recorded.
- [ ] Console is not clipped or overscanned.
- [ ] Touchscreen is detected as an input device.
- [ ] Touch event device and controller name recorded.
- [ ] Top-left touch verified.
- [ ] Top-right touch verified.
- [ ] Bottom-left touch verified.
- [ ] Bottom-right touch verified.
- [ ] Center touch verified.
- [ ] Touchscreen orientation and axis direction verified.
- [ ] Calibration requirement recorded.

## Power and thermal

- [ ] Power supply identity/rating recorded.
- [ ] No unresolved current or historical undervoltage flags.
- [ ] Baseline idle temperature recorded.
- [ ] Loaded maximum temperature recorded.
- [ ] No unresolved thermal throttling blocker.
- [ ] USB power-meter measurements recorded, or explicitly marked unavailable.

## GPIO buttons — pending physical button arrival

- [ ] A button verified on BCM 5.
- [ ] B button verified on BCM 6.
- [ ] C button verified on BCM 13.
- [ ] D button verified on BCM 19.
- [ ] PREV verified on BCM 26.
- [ ] NEXT verified on BCM 20.
- [ ] MENU verified on BCM 21.
- [ ] Active-low/pull-up behavior verified.
- [ ] 40 ms debounce behavior verified.
- [ ] No repeat, missed-press, or stuck-input blocker remains.

Keyboard simulation does not complete any GPIO checkbox.
