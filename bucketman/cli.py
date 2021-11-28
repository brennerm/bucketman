import warnings


import click

try:
    from bucketman.app import BucketManApp
except ModuleNotFoundError:
    import os
    import sys
    file_dir = os.path.dirname(__file__)
    sys.path.append(os.path.join(file_dir, '..'))
    from bucketman.app import BucketManApp

warnings.filterwarnings(action="ignore", message="unclosed", category=ResourceWarning)

@click.command()
@click.option('--endpoint-url', help="UNUSED")
@click.option('--client-id', help="UNUSED")
@click.option('--client-secret', help="UNUSED")
@click.option('--bucket', help="The S3 bucket to open.")
@click.option('--debug', is_flag=True, help='Enable debug logs.')
def main(endpoint_url, client_id, client_secret, bucket, debug):
    BucketManApp.run(title="bucketman", log="bucketman.log" if debug else None, bucket=bucket)

if __name__ == '__main__':
    main()