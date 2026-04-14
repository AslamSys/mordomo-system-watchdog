import os
import time
import json
import psutil
import docker
import asyncio
from typing import Dict, Any
from nats.aio.client import Client as NATS
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("watchdog")

NATS_URL = os.getenv("NATS_URL", "nats://infra-nats:4222")

# Containers categorizados do Mordomo
CRITICAL_CONTAINERS = {"infra-nats", "infra-postgres", "mordomo-orchestrator", "mordomo-brain"}
SACRIFICE_ORDER = [
    "mordomo-dashboard-ui",
    "mordomo-source-separation",
    "infra-grafana",
    "infra-prometheus"
]

class SystemWatchdog:
    def __init__(self):
        self.nc = NATS()
        try:
            self.docker_client = docker.from_env()
        except docker.errors.DockerException as e:
            logger.error(f"Erro ao conectar ao Docker. Tem certeza que montou o /var/run/docker.sock? Detalhes: {e}")
            self.docker_client = None

    async def connect(self):
        logger.info(f"Conectando ao NATS em {NATS_URL}...")
        try:
            await self.nc.connect(NATS_URL)
            logger.info("Conectado ao NATS com sucesso!")
        except Exception as e:
            logger.error(f"Falha ao conectar ao NATS: {e}")

    def get_cpu_temp(self) -> float:
        """Lê a temperatura termal física do Orange Pi"""
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                return int(f.read().strip()) / 1000.0
        except Exception:
            return 0.0

    def get_ram_usage(self) -> float:
        return psutil.virtual_memory().percent

    def evaluate_defcon_level(self, temp: float, ram: float) -> int:
        if temp > 85 or ram > 98: return 4
        if temp > 75 or ram > 90: return 3
        if temp > 65 or ram > 80: return 2
        return 1

    async def act_on_defcon(self, level: int, ram: float):
        if level <= 2 or not self.docker_client:
            return

        logger.warning(f"🔨 DEFCON {level} ATINGIDO! Iniciando ações defensivas.")
        
        for container_name in SACRIFICE_ORDER:
            try:
                container = self.docker_client.containers.get(container_name)
                if container.status == "running":
                    logger.warning(f"Sacrificando container: {container_name} para salvar o sistema. RAM em {ram}%")
                    container.stop(timeout=5)
                    
                    # Notifica todos que alguém foi sacrificado
                    await self.nc.publish("system.action.kill", json.dumps({
                        "container": container_name,
                        "reason": "OOM_PREVENTION" if ram > 90 else "THERMAL_PREVENTION",
                        "ram_usage": ram
                    }).encode())
                    
                    ram = self.get_ram_usage()
                    time.sleep(2)  # Dá um tempo para RAM esvaziar
                    
                    if self.evaluate_defcon_level(self.get_cpu_temp(), ram) < level:
                        logger.info("Sistema estabilizado após sacrifício.")
                        break
            except docker.errors.NotFound:
                continue
            except Exception as e:
                logger.error(f"Erro ao matar {container_name}: {e}")

    async def run_loop(self):
        await self.connect()

        while True:
            temp = self.get_cpu_temp()
            ram = self.get_ram_usage()
            level = self.evaluate_defcon_level(temp, ram)

            payload = {
                "cpu_temp": temp,
                "ram_usage_percent": ram,
                "defcon_level": level,
                "fan_speed_target": 100 if level > 2 else (70 if level == 2 else 30) # Futuramente controle real GPIO
            }

            logger.info(f"Monitor: Temp={temp}°C | RAM={ram}% | DEFCON={level}")

            if self.nc.is_connected:
                await self.nc.publish("system.health.status", json.dumps(payload).encode())

            if level >= 3:
                await self.act_on_defcon(level, ram)

            await asyncio.sleep(10)

if __name__ == "__main__":
    watchdog = SystemWatchdog()
    asyncio.run(watchdog.run_loop())
