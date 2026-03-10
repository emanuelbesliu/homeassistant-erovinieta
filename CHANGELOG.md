# Changelog

## [0.2.2](https://github.com/emanuelbesliu/homeassistant-erovinieta/compare/v0.2.1...v0.2.2) (2026-03-10)


### Bug Fixes

* rename price sensor to Payment Total and add vignette count attribute ([6fd9be7](https://github.com/emanuelbesliu/homeassistant-erovinieta/commit/6fd9be7f04b53ae9ddc34ca4149af43f3ef8c0ba))

## [0.2.1](https://github.com/emanuelbesliu/homeassistant-erovinieta/compare/v0.2.0...v0.2.1) (2026-03-10)


### Bug Fixes

* remove redundant binary_sensor (days_remaining already covers validity) ([4ffca57](https://github.com/emanuelbesliu/homeassistant-erovinieta/commit/4ffca57600eb7f073bf784ecfc26dc7f56f4d3aa))
* use DATE device class for expiry sensor to show actual date instead of relative time ([43cc088](https://github.com/emanuelbesliu/homeassistant-erovinieta/commit/43cc0886305c55f3ef4b249cfd3ae9e715d7f8c7))

## [0.2.0](https://github.com/emanuelbesliu/homeassistant-erovinieta/compare/erovinieta-v0.1.1...erovinieta-v0.2.0) (2026-03-10)


### Features

* initial eRovinieta integration for Home Assistant ([16a26c4](https://github.com/emanuelbesliu/homeassistant-erovinieta/commit/16a26c492bf42bca15c472d40bb0275fceff6719))


### Bug Fixes

* pin ddddocr&lt;1.5.0 (breaking API change in 1.5.x), add CONFIG_SCHEMA for hassfest ([93e1497](https://github.com/emanuelbesliu/homeassistant-erovinieta/commit/93e14977b135dc5381a30c4de1952340262fdfcd))
* replace ddddocr with Pillow-based template OCR for Python 3.14+ compatibility ([fbfec0f](https://github.com/emanuelbesliu/homeassistant-erovinieta/commit/fbfec0f29a9dd2e0a906e71da5107eb607a96ddb))
* resolve options flow crash and captcha i/l confusion ([031f7c6](https://github.com/emanuelbesliu/homeassistant-erovinieta/commit/031f7c698c09dca3d598bc926e55e92d2f880fc2))
* use Python 3.12 in CI (ddddocr incompatible with 3.13), add workflow_dispatch to release-please, include brand/ in release zip ([b86c8cb](https://github.com/emanuelbesliu/homeassistant-erovinieta/commit/b86c8cbaf8c640167c063fad5a82d81b62a30e2b))
* work around ddddocr 1.6.0 broken import on Python 3.13+ ([5a83d65](https://github.com/emanuelbesliu/homeassistant-erovinieta/commit/5a83d651f048e5f8e6a631fd9a3bc1e4198f7ac5))

## [0.1.1](https://github.com/emanuelbesliu/homeassistant-erovinieta/compare/v0.1.0...v0.1.1) (2026-03-10)


### Bug Fixes

* replace ddddocr with Pillow-based template OCR for Python 3.14+ compatibility ([fbfec0f](https://github.com/emanuelbesliu/homeassistant-erovinieta/commit/fbfec0f29a9dd2e0a906e71da5107eb607a96ddb))

## 0.1.0 (2026-03-09)


### Features

* initial eRovinieta integration for Home Assistant ([16a26c4](https://github.com/emanuelbesliu/homeassistant-erovinieta/commit/16a26c492bf42bca15c472d40bb0275fceff6719))


### Bug Fixes

* pin ddddocr&lt;1.5.0 (breaking API change in 1.5.x), add CONFIG_SCHEMA for hassfest ([93e1497](https://github.com/emanuelbesliu/homeassistant-erovinieta/commit/93e14977b135dc5381a30c4de1952340262fdfcd))
* use Python 3.12 in CI (ddddocr incompatible with 3.13), add workflow_dispatch to release-please, include brand/ in release zip ([b86c8cb](https://github.com/emanuelbesliu/homeassistant-erovinieta/commit/b86c8cbaf8c640167c063fad5a82d81b62a30e2b))
* work around ddddocr 1.6.0 broken import on Python 3.13+ ([5a83d65](https://github.com/emanuelbesliu/homeassistant-erovinieta/commit/5a83d651f048e5f8e6a631fd9a3bc1e4198f7ac5))
