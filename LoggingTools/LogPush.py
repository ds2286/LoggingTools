# library
import logging
import os

# installed
import boto3
from botocore.exceptions import (
    NoCredentialsError, 
    ClientError
)

# custom
from LoggingTools.settings import S3Settings
from LoggingTools.LoggingHelper import LoggerFactory




# Set up logging
logging_factory = LoggerFactory()
if LoggerFactory.is_logging_configured():        
    logging_factory.add_logger_from_yaml()
else:
    logging_factory.setup_logger(dynamic_log_filename=True)

logger = logging_factory.get_logger("push_logger")


class S3Uploader:
    def __init__(
        self, 
        s3_settings: S3Settings = None
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
        Upload a single file to S3 and delete it locally if the upload is successful.
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
                f"Successfully uploaded {file_path} " +
                f"to {self.s3_settings.bucket_name}/{s3_key}"
            )
            # Remove the file locally after successful upload
            os.remove(file_path)
            logger.info(f"Deleted local file {file_path} after upload.")
        except FileNotFoundError:
            logger.error(f'File {file_path} not found.')
        except NoCredentialsError:
            logger.error('Credentials not available.')
        except ClientError as e:
            logger.error(f'Failed to upload {file_path} to S3: {e}')

    def upload_directory(
        self,
        directory_to_upload: str = None,
        use_filename_only: bool = False
    ):
        """
        Upload all files in the directory to S3, preserving the directory structure
        unless use_filename_only is True.
        
        :param directory_to_upload: Local directory path to upload
        :param use_filename_only: If True, only the file name is used as the S3 key.
        """
        if not directory_to_upload:
            directory_to_upload = self.s3_settings.upload_directory

        for root, _, files in os.walk(directory_to_upload):
            for file in files:
                file_path = os.path.join(root, file)
                
                # Determine the S3 key based on use_filename_only
                if use_filename_only:
                    s3_key = file  # Only the file name
                else:
                    # Create S3 key by stripping the base directory from the file path to preserve structure
                    s3_key = os.path.relpath(file_path, directory_to_upload)
                
                if self.s3_settings.key_prefix:
                    s3_key = os.path.join(self.s3_settings.key_prefix, s3_key)
                
                self.upload_file(file_path, s3_key)
        
        logger.info(f'Upload of directory {directory_to_upload} complete.')


# Function to get the log file path
def get_log_file_path(logger) -> str:
    """
    Get the log file path from the logger.
    :param logger: Logger object
    :return: Log file path
    """
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            return handler.baseFilename
    return None


def push_logs(
    directory_to_upload: str = None,
    env_path: str = os.getenv("ENV_PATH"),
    use_filename_only: bool = True
):
    """ Push logs to S3 bucket.
    
    :param directory_to_upload: Local directory path to upload
    :param env_path: Path to the environment file
    :param use_filename_only: If True, only the file name is used with the S3 key.
    """
    
    # Create an instance of S3Uploader
    uploader = S3Uploader(
        s3_settings=S3Settings(
            _env_file=env_path
        )
    )
    
    # Upload all files in the directory to the S3 bucket
    uploader.upload_directory(
        directory_to_upload=directory_to_upload,
        use_filename_only=use_filename_only
    )

if __name__ == '__main__':
    
    push_logs()