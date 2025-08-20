#!/usr/bin/env python3
"""
Versão simplificada do CDK app para bootstrap inicial
"""

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    RemovalPolicy,
    Duration,
    CfnOutput
)
from constructs import Construct

class SimpleStorageStack(Stack):
    """Stack simplificada apenas com S3"""
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Referência ao bucket existente (não criar novo)
        self.data_bucket = s3.Bucket.from_bucket_name(
            self,
            "DataBucket",
            bucket_name="pncp-extractor-data-prod-566387937580"
        )
        
        # Output do bucket
        CfnOutput(
            self,
            "DataBucketName",
            value=self.data_bucket.bucket_name,
            description="Nome do bucket S3 para dados PNCP"
        )

def main():
    app = cdk.App()
    
    SimpleStorageStack(
        app, 
        "PNCPExtractorSimpleStack",
        env=cdk.Environment(
            account="566387937580",
            region="us-east-2"
        )
    )
    
    app.synth()

if __name__ == "__main__":
    main()