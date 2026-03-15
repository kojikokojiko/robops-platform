"""
RobOps Platform - AWS アーキテクチャ図生成スクリプト
出力: docs/architecture.png
"""

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.database import Dynamodb
from diagrams.aws.integration import Eventbridge
from diagrams.aws.iot import IotCore, IotRule, IotJobs
from diagrams.aws.network import APIGateway
from diagrams.aws.storage import S3
from diagrams.onprem.container import Docker
from diagrams.onprem.client import User
from diagrams.programming.framework import React

graph_attr = {
    "fontsize": "14",
    "bgcolor": "white",
    "pad": "0.5",
    "splines": "ortho",
    "nodesep": "0.6",
    "ranksep": "0.9",
}

with Diagram(
    "RobOps Platform - Architecture",
    filename="docs/architecture",
    outformat="png",
    show=False,
    direction="TB",
    graph_attr=graph_attr,
):
    browser = User("ブラウザ")

    # ─── ローカル PC ───────────────────────────────────────
    with Cluster("開発者の PC"):
        dashboard = React("React Dashboard\n(Vite :5173)")

        with Cluster("Docker Compose (エミュレータ)"):
            robots = [
                Docker("robot-001"),
                Docker("robot-002"),
                Docker("robot-003"),
                Docker("robot-004"),
                Docker("robot-005"),
            ]

    # ─── AWS CLOUD ─────────────────────────────────────────
    with Cluster("AWS Cloud"):

        # API Gateway
        apigw = APIGateway("API Gateway\nHTTP API + WebSocket")

        # Lambda
        fn = Lambda("Lambda\n(FastAPI / Mangum)")

        # IoT Core
        with Cluster("AWS IoT Core"):
            iot = IotCore("MQTT Broker\nIoT Registry")
            iot_rule = IotRule("IoT Rules")
            iot_jobs = IotJobs("IoT Jobs\n(OTA)")

        # Data / Integration
        dynamo = Dynamodb("DynamoDB\nロボット状態\n+テレメトリ履歴")
        eb = Eventbridge("EventBridge\nスケジューラー")
        s3 = S3("S3\nOTA マニフェスト")

    # ─── 接続 ──────────────────────────────────────────────

    # ブラウザ → React
    browser >> Edge(label="HTTPS") >> dashboard

    # React → API Gateway
    dashboard >> Edge(label="HTTPS / WSS") >> apigw

    # エミュレータ → IoT Core (MQTT/TLS)
    for robot in robots:
        robot >> Edge(label="MQTT/TLS", color="darkorange") >> iot

    # API Gateway → Lambda
    apigw >> Edge(label="invoke") >> fn

    # Lambda ↔ IoT Core (コマンド送信 / OTA)
    fn >> Edge(label="publish\n(commands)") >> iot
    fn >> Edge(label="put manifest", color="darkgreen") >> s3
    fn >> Edge(label="create job") >> iot_jobs
    iot_jobs >> Edge(label="job document\n(manifest URL)", color="darkgreen") >> iot

    # IoT Core → Lambda (テレメトリ処理)
    iot >> Edge(label="telemetry") >> iot_rule
    iot_rule >> Edge(label="invoke\n(telemetry\nprocessor)", color="firebrick") >> fn

    # Lambda → DynamoDB
    fn >> Edge(label="read / write") >> dynamo

    # Lambda ↔ EventBridge
    fn >> Edge(label="put rule") >> eb
    eb >> Edge(label="invoke\n(scheduler\ntrigger)", color="steelblue") >> fn
