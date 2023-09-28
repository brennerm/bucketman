# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.3.0] - 2023-09-28

## Added

- implement deletion of S3 object(s)
- implement upload of local file(s) to S3
- implement download of S3 object(s)
- allow to switch between S3 buckets
- implement dry run mode which disables all write operations

## Changed

- migrate codebase to new Textual version 0.38.1

## Removed

- remove components that have been replaced with built-in Textual components

## [v0.2.0] - 2021-12-01

### Added

- implement dynamic context aware key bindings
- allow to set authentication params via CLI

### Fixed

- prevent crash on reload in certain scenarios
- exit gracefully when S3 bucket can't be accessed

## [v0.1.0] - 2021-11-28

### Added

- initial release
