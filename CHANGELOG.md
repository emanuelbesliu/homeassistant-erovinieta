# Changelog

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
