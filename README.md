# 🐕 System Watchdog

## 🔗 Navegação

**[🏠 AslamSys](https://github.com/AslamSys)** → **[📚 _system](https://github.com/AslamSys/_system)** → **[📂 Aslam (Orange Pi 5 16GB)](https://github.com/AslamSys/_system/blob/main/hardware/mordomo%20-%20(orange-pi-5-16gb)/README.md)** → **mordomo-system-watchdog**

### Containers Relacionados (aslam)
- [mordomo-audio-bridge](https://github.com/AslamSys/mordomo-audio-bridge)
- [mordomo-audio-capture-vad](https://github.com/AslamSys/mordomo-audio-capture-vad)
- [mordomo-wake-word-detector](https://github.com/AslamSys/mordomo-wake-word-detector)
- [mordomo-speaker-verification](https://github.com/AslamSys/mordomo-speaker-verification)
- [mordomo-whisper-asr](https://github.com/AslamSys/mordomo-whisper-asr)
- [mordomo-speaker-id-diarization](https://github.com/AslamSys/mordomo-speaker-id-diarization)
- [mordomo-source-separation](https://github.com/AslamSys/mordomo-source-separation)
- [mordomo-core-gateway](https://github.com/AslamSys/mordomo-core-gateway)
- [mordomo-orchestrator](https://github.com/AslamSys/mordomo-orchestrator)
- [mordomo-brain](https://github.com/AslamSys/mordomo-brain)
- [mordomo-tts-engine](https://github.com/AslamSys/mordomo-tts-engine)
- [mordomo-openclaw-agent](https://github.com/AslamSys/mordomo-openclaw-agent)

---

**Container:** `system-watchdog`  
**Ecossistema:** Mordomo  
**Posição no Fluxo:** Monitoramento Ativo e Proteção de Hardware

---

## 📋 Propósito

Guardião silencioso que monitora a saúde física do Orange Pi 5 (Temperatura, RAM, CPU) e toma ações corretivas automáticas para evitar travamentos ou danos ao hardware. Garante que o Core vital nunca pare, sacrificando serviços supérfluos se necessário.

---

## 🎯 Responsabilidades

### Primárias
- ✅ **Monitorar Temperatura da CPU/NPU** (via `/sys/class/thermal`)
- ✅ **Monitorar Uso de RAM** (via Docker Stats API)
- ✅ **Controle Térmico Ativo:** Ajustar velocidade da ventoinha (PWM) baseado na temperatura
- ✅ **OOM Prevention (Out of Memory):** Matar containers não-críticos se a RAM acabar
- ✅ **Health Checks:** Reiniciar containers travados que não respondem ao NATS

### Secundárias
- ✅ Publicar métricas de saúde no NATS (`system.health.status`)
- ✅ Alertar usuário se o hardware estiver em perigo (via TTS/Notificação)
- ✅ Logar incidentes térmicos ou de memória para análise

---

## 🔄 Níveis de Defesa (DEFCON)

### 🟢 Nível 1: Normal (Idle/Carga Leve)
- **Condição:** Temp < 60°C, RAM < 70%
- **Ação:** Ventoinha em 30% (silencioso), monitoramento a cada 10s.

### 🟡 Nível 2: Alerta (Carga Média)
- **Condição:** Temp > 65°C **OU** RAM > 80%
- **Ação:** 
  - Ventoinha em 70%.
  - Publica alerta `system.health.warning`.
  - Pausa tarefas de fundo (ex: indexação Qdrant, downloads).

### 🟠 Nível 3: Crítico (Sobrecarga)
- **Condição:** Temp > 75°C **OU** RAM > 90%
- **Ação:** 
  - Ventoinha em 100% (Máximo).
  - **Sacrifício Tático:** Para containers não-essenciais:
    1. `source-separation` (Recurso pesado de áudio)
    3. `monitoramento` (Grafana/Prometheus - cegueira temporária aceitável)
  - Notifica usuário: "Estou sobrecarregado, desativando sistemas secundários."

### 🔴 Nível 4: Emergência (Perigo de Dano)
- **Condição:** Temp > 85°C **OU** RAM > 98%
- **Ação:** 
  - Mata TUDO exceto `core` (Brain/Manager) e `infra` (NATS).
  - Se Temp > 90°C: **Shutdown ordenado do sistema operacional.**

---

## 🔧 Tecnologias

**Linguagem:** Python (leve e acesso fácil a hardware) ou Go (binário único, zero deps)

**Bibliotecas:**
- `docker-py`: Para controlar containers (stop/restart).
- `psutil`: Para métricas de sistema precisas.
- `RPi.GPIO` (ou equivalente Orange Pi): Para controle PWM da ventoinha.
- `nats-py`: Para comunicação.

---

## 📊 Especificações

```yaml
Recursos:
  CPU: < 1% (Polling a cada 5-10s)
  RAM: ~ 20 MB
  Privilégios: Root/Privileged (necessário para acessar hardware e Docker socket)

Hardware Access:
  - /var/run/docker.sock (Docker API)
  - /sys/class/thermal/ (Sensores Temp)
  - /sys/class/pwm/ (Controle Ventoinha)
```

---

## 🔌 Integração NATS

### Eventos Publicados
```json
// Status periódico (Heartbeat)
subject: "system.health.status"
payload: {
  "cpu_temp": 55.4,
  "ram_usage_percent": 42.5,
  "fan_speed": 30,
  "defcon_level": 1
}

// Alerta de ação corretiva
subject: "system.action.kill"
payload: {
  "container": "source-separation",
  "reason": "OOM_PREVENTION",
  "ram_usage": 92.1
}
```

### Comandos Recebidos
```json
// Controle manual (Admin)
subject: "system.fan.set"
payload: { "speed": 100 }
```
