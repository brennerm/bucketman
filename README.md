# bucketman <img src="img/logo.png" width="20px">

A terminal application for exploring and interacting (coming soon) with S3 buckets.

![screenshot](img/screenshot.png)

## installation

```bash
$ pip install bucketman
$ bucketman --help
```

## authentication

bucketman uses the boto3 library for interacting with your S3 buckets. Thus it supports the same ways of [providing your credentials](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html).

Additionally you can pass your access and secret key using the `--access-key-id` and `--secret-access-key` parameters as well as providing a custom endpoint URL with `--endpoint-url` for non-AWS S3 buckets.

## features

- browse through S3 buckets
- switch between S3 buckets
- browse through local directories
- delete S3 objects

## planned features

- copy files from local to S3 and vice versa
- copy files from one S3 bucket to another
- move/rename S3 objects
- set ACL and metadata of S3 objects
- support S3 bucket pagination
