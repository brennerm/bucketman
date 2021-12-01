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

class RequiredIf(click.Option):
    def __init__(self, *args, **kwargs):
        self.required_if = kwargs.pop('required_if')
        assert self.required_if, "'required_if' is parameter required"
        kwargs['help'] = (kwargs.get('help', '') +
            f' NOTE: This argument requires setting {self.required_if}').strip()
        super(RequiredIf, self).__init__(*args, **kwargs)

    def handle_parse_result(self, ctx: click.core.Context, opts, args):
        we_are_present = self.name in opts
        other_present = self.required_if in opts

        if we_are_present != other_present:
            raise click.UsageError(
                f"Illegal usage: `{self.name}` requires setting `{self.required_if}`")
        else:
            self.prompt = None

        return super(RequiredIf, self).handle_parse_result(ctx, opts, args)

@click.command()
@click.option('--endpoint-url', help="Overwrite the S3 endpoint URL, e.g. when using a non-AWS S3 bucket.")
@click.option('--access-key-id', help="Set the access key ID used for authentication.", cls=RequiredIf, required_if='secret_access_key')
@click.option('--secret-access-key', help="Set the secret access key used for authentication.", cls=RequiredIf, required_if='access_key_id')
@click.option('--bucket', help="Set the S3 bucket to open.")
@click.option('--debug', is_flag=True, help='Enable debug logs.')
def main(endpoint_url, access_key_id, secret_access_key, bucket, debug):
    BucketManApp.run(
        title="bucketman",
        log="bucketman.log" if debug else None,
        bucket=bucket,
        endpoint_url=endpoint_url,
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
    )

if __name__ == '__main__':
    main()