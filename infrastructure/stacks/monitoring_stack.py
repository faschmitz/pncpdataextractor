"""
Monitoring Stack para PNCP Data Extractor

Esta stack define recursos de monitoramento:
- CloudWatch Dashboards
- CloudWatch Alarms
- Métricas customizadas
- Integração com SNS para alertas
"""

from aws_cdk import (
    Stack,
    aws_cloudwatch as cloudwatch,
    aws_logs as logs,
    Duration,
    CfnOutput
)
from constructs import Construct
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .compute_stack import ComputeStack
    from .orchestration_stack import OrchestrationStack

class MonitoringStack(Stack):
    """Stack para monitoramento e observabilidade"""
    
    def __init__(
        self, 
        scope: Construct, 
        construct_id: str,
        compute_stack: "ComputeStack",
        orchestration_stack: "OrchestrationStack",
        app_name: str,
        environment: str,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.compute_stack = compute_stack
        self.orchestration_stack = orchestration_stack
        self.app_name = app_name
        self.env_name = environment
        
        # Criar recursos de monitoramento
        self._create_cloudwatch_alarms()
        self._create_custom_metrics()
        self._create_dashboard()
        self._create_log_insights_queries()
        self._create_outputs()
    
    def _create_cloudwatch_alarms(self):
        """Criar alarmes do CloudWatch"""
        
        # Alarme para falhas na execução do Step Functions
        self.step_functions_failure_alarm = cloudwatch.Alarm(
            self,
            "StepFunctionsFailureAlarm",
            alarm_name=f"{self.app_name}-stepfunctions-failures-{self.env_name}",
            alarm_description="Alarme para falhas na execução do Step Functions",
            metric=cloudwatch.Metric(
                namespace="AWS/States",
                metric_name="ExecutionsFailed",
                dimensions_map={
                    "StateMachineArn": self.orchestration_stack.state_machine.state_machine_arn
                },
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        # Adicionar ação para notificar via SNS
        self.step_functions_failure_alarm.add_alarm_action(
            cloudwatch.SnsAction(self.orchestration_stack.alerts_topic)
        )
        
        # Alarme para execuções muito longas
        self.step_functions_duration_alarm = cloudwatch.Alarm(
            self,
            "StepFunctionsDurationAlarm",
            alarm_name=f"{self.app_name}-stepfunctions-duration-{self.env_name}",
            alarm_description="Alarme para execuções muito longas do Step Functions",
            metric=cloudwatch.Metric(
                namespace="AWS/States",
                metric_name="ExecutionTime",
                dimensions_map={
                    "StateMachineArn": self.orchestration_stack.state_machine.state_machine_arn
                },
                statistic="Average",
                period=Duration.minutes(5)
            ),
            threshold=7200000,  # 2 horas em millisegundos
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        self.step_functions_duration_alarm.add_alarm_action(
            cloudwatch.SnsAction(self.orchestration_stack.alerts_topic)
        )
        
        # Alarme para falhas nas tasks ECS
        self.ecs_task_failure_alarm = cloudwatch.Alarm(
            self,
            "ECSTaskFailureAlarm",
            alarm_name=f"{self.app_name}-ecs-task-failures-{self.env_name}",
            alarm_description="Alarme para falhas nas tasks ECS",
            metric=cloudwatch.Metric(
                namespace="AWS/ECS",
                metric_name="ServiceTasksFailed",
                dimensions_map={
                    "ClusterName": self.compute_stack.ecs_cluster.cluster_name
                },
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        self.ecs_task_failure_alarm.add_alarm_action(
            cloudwatch.SnsAction(self.orchestration_stack.alerts_topic)
        )
        
        # Alarme para erros nos logs
        self.application_error_alarm = cloudwatch.Alarm(
            self,
            "ApplicationErrorAlarm",
            alarm_name=f"{self.app_name}-application-errors-{self.env_name}",
            alarm_description="Alarme para erros na aplicação (logs)",
            metric=logs.FilterMetric(
                log_group=self.compute_stack.log_group,
                metric_namespace=f"{self.app_name}/Application",
                metric_name="ErrorCount",
                filter_pattern=logs.FilterPattern.any_term("ERROR", "FATAL", "Exception", "Traceback"),
                metric_value="1"
            ).with_(
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=5,  # Mais de 5 erros em 5 minutos
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        self.application_error_alarm.add_alarm_action(
            cloudwatch.SnsAction(self.orchestration_stack.alerts_topic)
        )
        
        # Alarme para pouco espaço em S3 (caso haja limite)
        # Nota: S3 não tem limites de espaço, mas podemos monitorar custos
        
        # Alarme para APIs OpenAI com muitas falhas
        self.openai_api_failure_alarm = cloudwatch.Alarm(
            self,
            "OpenAIAPIFailureAlarm",
            alarm_name=f"{self.app_name}-openai-api-failures-{self.env_name}",
            alarm_description="Alarme para muitas falhas na API OpenAI",
            metric=logs.FilterMetric(
                log_group=self.compute_stack.log_group,
                metric_namespace=f"{self.app_name}/OpenAI",
                metric_name="APIFailureCount",
                filter_pattern=logs.FilterPattern.any_term("OpenAI", "API", "429", "quota", "rate limit"),
                metric_value="1"
            ).with_(
                statistic="Sum",
                period=Duration.minutes(10)
            ),
            threshold=10,  # Mais de 10 falhas de API em 10 minutos
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        self.openai_api_failure_alarm.add_alarm_action(
            cloudwatch.SnsAction(self.orchestration_stack.alerts_topic)
        )
    
    def _create_custom_metrics(self):
        """Criar métricas customizadas para aplicação"""
        
        # Métricas que serão enviadas pela aplicação via CloudWatch SDK
        
        # Métrica de registros extraídos por dia
        self.records_extracted_metric = cloudwatch.Metric(
            namespace=f"{self.app_name}/Extraction",
            metric_name="RecordsExtracted",
            statistic="Sum",
            period=Duration.hours(24)
        )
        
        # Métrica de registros aprovados pelo filtro LLM
        self.records_approved_metric = cloudwatch.Metric(
            namespace=f"{self.app_name}/Filter",
            metric_name="RecordsApproved",
            statistic="Sum", 
            period=Duration.hours(24)
        )
        
        # Métrica de custo estimado OpenAI
        self.openai_cost_metric = cloudwatch.Metric(
            namespace=f"{self.app_name}/Cost",
            metric_name="OpenAICostUSD",
            statistic="Sum",
            period=Duration.hours(24)
        )
        
        # Métrica de tempo de execução total
        self.execution_duration_metric = cloudwatch.Metric(
            namespace=f"{self.app_name}/Performance",
            metric_name="ExecutionDurationMinutes",
            statistic="Average",
            period=Duration.hours(24)
        )
        
        # Alarme para custo muito alto da OpenAI
        self.openai_cost_alarm = cloudwatch.Alarm(
            self,
            "OpenAICostAlarm",
            alarm_name=f"{self.app_name}-openai-cost-{self.env_name}",
            alarm_description="Alarme para custos elevados da API OpenAI",
            metric=self.openai_cost_metric,
            threshold=50.0,  # $50 USD por dia
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        self.openai_cost_alarm.add_alarm_action(
            cloudwatch.SnsAction(self.orchestration_stack.alerts_topic)
        )
    
    def _create_dashboard(self):
        """Criar dashboard do CloudWatch"""
        
        self.dashboard = cloudwatch.Dashboard(
            self,
            "PNCPExtractorDashboard",
            dashboard_name=f"{self.app_name}-dashboard-{self.env_name}",
            period_override=cloudwatch.PeriodOverride.AUTO,
            start="-P7D"  # Últimos 7 dias por padrão
        )
        
        # Widget de métricas principais
        main_metrics_widget = cloudwatch.GraphWidget(
            title="Métricas Principais de Extração",
            width=12,
            height=6,
            left=[
                self.records_extracted_metric,
                self.records_approved_metric
            ],
            right=[
                cloudwatch.Metric(
                    namespace="AWS/States",
                    metric_name="ExecutionsSucceeded",
                    dimensions_map={
                        "StateMachineArn": self.orchestration_stack.state_machine.state_machine_arn
                    },
                    statistic="Sum",
                    period=Duration.hours(24)
                )
            ],
            legend_position=cloudwatch.LegendPosition.BOTTOM
        )
        
        # Widget de performance
        performance_widget = cloudwatch.GraphWidget(
            title="Performance e Duração",
            width=12,
            height=6,
            left=[self.execution_duration_metric],
            right=[
                cloudwatch.Metric(
                    namespace="AWS/ECS",
                    metric_name="CPUUtilization",
                    dimensions_map={
                        "ClusterName": self.compute_stack.ecs_cluster.cluster_name
                    },
                    statistic="Average",
                    period=Duration.minutes(5)
                ),
                cloudwatch.Metric(
                    namespace="AWS/ECS", 
                    metric_name="MemoryUtilization",
                    dimensions_map={
                        "ClusterName": self.compute_stack.ecs_cluster.cluster_name
                    },
                    statistic="Average",
                    period=Duration.minutes(5)
                )
            ]
        )
        
        # Widget de custos
        cost_widget = cloudwatch.GraphWidget(
            title="Custos OpenAI",
            width=12,
            height=6,
            left=[self.openai_cost_metric],
            legend_position=cloudwatch.LegendPosition.BOTTOM,
            view=cloudwatch.GraphWidgetView.TIME_SERIES,
            statistic="Sum"
        )
        
        # Widget de alarmes
        alarms_widget = cloudwatch.AlarmStatusWidget(
            title="Status dos Alarmes",
            width=12,
            height=4,
            alarms=[
                self.step_functions_failure_alarm,
                self.ecs_task_failure_alarm,
                self.application_error_alarm,
                self.openai_api_failure_alarm,
                self.openai_cost_alarm
            ]
        )
        
        # Widget de logs recentes
        logs_widget = cloudwatch.LogQueryWidget(
            title="Logs de Erro Recentes",
            width=24,
            height=6,
            log_groups=[self.compute_stack.log_group],
            query_lines=[
                "fields @timestamp, @message",
                "filter @message like /ERROR|FATAL|Exception/",
                "sort @timestamp desc",
                "limit 100"
            ]
        )
        
        # Adicionar widgets ao dashboard
        self.dashboard.add_widgets(
            main_metrics_widget,
            performance_widget,
            cost_widget,
            alarms_widget,
            logs_widget
        )
    
    def _create_log_insights_queries(self):
        """Criar queries salvas para CloudWatch Logs Insights"""
        
        # Query para análise de performance do filtro LLM
        self.llm_performance_query = logs.QueryDefinition(
            self,
            "LLMPerformanceQuery",
            query_definition_name=f"{self.app_name}-llm-performance-{self.env_name}",
            query_string="""
            fields @timestamp, @message
            | filter @message like /LLM/
            | parse @message "Tokens: *, Custo: $*" as tokens, cost
            | stats avg(tokens) as avg_tokens, sum(cost) as total_cost by bin(5m)
            | sort @timestamp desc
            """,
            log_groups=[self.compute_stack.log_group]
        )
        
        # Query para análise de erros
        self.error_analysis_query = logs.QueryDefinition(
            self,
            "ErrorAnalysisQuery",
            query_definition_name=f"{self.app_name}-error-analysis-{self.env_name}",
            query_string="""
            fields @timestamp, @message, @logStream
            | filter @message like /ERROR|FATAL|Exception|Traceback/
            | stats count() as error_count by bin(1h)
            | sort @timestamp desc
            """,
            log_groups=[self.compute_stack.log_group]
        )
        
        # Query para análise da API PNCP
        self.pncp_api_query = logs.QueryDefinition(
            self,
            "PNCPAPIQuery",
            query_definition_name=f"{self.app_name}-pncp-api-analysis-{self.env_name}",
            query_string="""
            fields @timestamp, @message
            | filter @message like /API|requisição|Modalidade/
            | parse @message "Modalidade *: * registros em * páginas" as modalidade, records, pages
            | stats sum(records) as total_records, sum(pages) as total_pages by modalidade
            | sort total_records desc
            """,
            log_groups=[self.compute_stack.log_group]
        )
    
    def _create_outputs(self):
        """Criar outputs para referência"""
        
        # Dashboard URL
        CfnOutput(
            self,
            "DashboardURL",
            value=f"https://{self.region}.console.aws.amazon.com/cloudwatch/home?region={self.region}#dashboards:name={self.dashboard.dashboard_name}",
            description="URL do Dashboard CloudWatch",
            export_name=f"{self.stack_name}-DashboardURL"
        )
        
        # ARNs dos alarmes principais
        CfnOutput(
            self,
            "MainAlarmsArns",
            value=",".join([
                self.step_functions_failure_alarm.alarm_arn,
                self.ecs_task_failure_alarm.alarm_arn,
                self.application_error_alarm.alarm_arn
            ]),
            description="ARNs dos alarmes principais",
            export_name=f"{self.stack_name}-MainAlarmsArns"
        )
        
        # Nome do dashboard
        CfnOutput(
            self,
            "DashboardName",
            value=self.dashboard.dashboard_name,
            description="Nome do Dashboard CloudWatch",
            export_name=f"{self.stack_name}-DashboardName"
        )