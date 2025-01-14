from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from airflow.hooks.postgres_hook import PostgresHook
from airflow.contrib.hooks.aws_hook import AwsHook


class StageToRedshiftOperator(BaseOperator):
    ui_color = '#358140'
    copy_query = """
                COPY {schema}.{table}
                FROM 's3://{s3_bucket}/{s3_prefix}'
                ACCESS_KEY_ID '{access_key}'
                SECRET_ACCESS_KEY '{secret_key}';
                """

    @apply_defaults
    def __init__(self,
                 # Define your operators params (with defaults) here
                 s3_bucket="",
                 s3_prefix="",
                 schema,
                 table,
                 aws_conn_id="aws_credentials",
                 redshift_conn_id="redshift",
                 *args, **kwargs):

        super(StageToRedshiftOperator, self).__init__(*args, **kwargs)
        self.aws_conn_id = aws_conn_id
        self.redshift_conn_id = redshift_conn_id
        self.s3_bucket = s3_bucket
        self.s3_prefix = s3_prefix
        self.schema = schema
        self.table = table

    def execute(self, context):
        """Execute function for every operator
        Airflow calls this execute function to actually execute the operator when it's time for the task to run.
        """
        # Connections to external systems(AWS) and databases(AWS Redshift)
        # With Hooks, we can interact with AWS and Redshift
        self.log.info('Starting COPY command...')    
        aws_hook = AwsHook(aws_conn_id=self.aws_conn_id)
        credentials = aws_hook.get_credentials()
        redshift_hook = PostgresHook(postgres_conn_id=self.redshift_conn_id)

        # Clear all data in the destination table in Redshift if there is some data in that table.
        self.log.info(f"Removing data from Redshift, if table {self.schema}.{self.table} already exists in Redshift")
        redshift_hook.run(f"DELETE FROM {self.schema}.{self.table}")

        # Use COPY command to load data in parallel from data files existing on S3 into Redshift
        self.log.info("Copying data from S3 to Redshift")
        formatted_query = StageToRedshiftOperator.copy_query.format(
            schema=self.schema,
            table=self.table,
            s3_bucket=self.s3_bucket,
            s3_prefix=self.s3_prefix,
            access_key=credentials.access_key,
            secret_key=credentials.secret_key,
            )

        # Running copy_query to copy and then load data from S3 to Redshift
        self.log.info("Executing COPY command...")
        redshift_hook.run(formatted_query)
        self.log.info(f"COPY command complete, successfully loaded data from S3 to Redshift table {self.schema}.{self.table}!")