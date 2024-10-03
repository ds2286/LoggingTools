# library
import os

# installed
import boto3
from botocore.exceptions import (
    NoCredentialsError, 
    ClientError
)

# custom
from settings import S3Settings
from LoggingTools import LoggerFactory




# Set up logging
logging_factory = LoggerFactory()
if LoggerFactory.is_logger_configured():        
    logging_factory.add_logger_from_yaml()
else:
    logging_factory.setup_logger()

logger = logging_factory.get_logger("push_logger")


class S3Uploader:
    def __init__(
        self, 
        s3_settings: S3Settings=None
    ):
        """
        Initialize the S3Uploader with credentials and bucket information.
        """
        self.s3_settings = s3_settings or S3Settings()
        self.s3_client = self._create_s3_client()

    def _create_s3_client(self):
        """
        Create the S3 client to connect to OpenStack's S3 endpoint.
        """
        return boto3.client(
            's3',
            aws_access_key_id=self.s3_settings.access_key,
            aws_secret_access_key=self.s3_settings.secret_key,
            endpoint_url=self.s3_settings.endpoint_url,
            region_name=self.s3_settings.region
        )

    def upload_file(self, file_path: str, s3_key: str):
        """
        Upload a single file to S3.
        :param file_path: Local path of the file to upload
        :param s3_key: S3 key for the file in the bucket
        """
        try:
            self.s3_client.upload_file(
                file_path, 
                self.s3_settings.bucket_name, 
                s3_key
            )
            logger.info(
                f"Successfully uploaded {file_path} " + \
                "to {self.s3_settings.bucket_name}/{s3_key}"
            )
        except FileNotFoundError:
            logger.info(f'File {file_path} not found.')
        except NoCredentialsError:
            logger.info('Credentials not available.')
        except ClientError as e:
            logger.info(f'Failed to upload {file_path} to S3: {e}')

    def upload_directory(
        self, 
        directory_to_upload: str=None
    ):
        """
        Upload all files in the directory to S3, preserving the directory structure.
        :param directory: Local directory path to upload
        """
        if not directory_to_upload:
            directory_to_upload = self.s3_settings.upload_directory
        
        for root, _, files in os.walk(directory_to_upload):
            for file in files:
                file_path = os.path.join(root, file)
                # Create S3 key by stripping the base directory from the file path to preserve structure
                s3_key = os.path.relpath(file_path, directory_to_upload)
                self.upload_file(file_path, s3_key)
        
        logger.info(f'Upload of directory {directory_to_upload} complete.')

if __name__ == '__main__':
    
    # Create an instance of S3Uploader
    uploader = S3Uploader()

    # Upload all files in the directory to the S3 bucket
    uploader.upload_directory()
