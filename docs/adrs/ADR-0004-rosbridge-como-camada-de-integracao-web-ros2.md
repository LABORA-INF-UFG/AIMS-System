# ADR-0004: Rosbridge como Camada de Integração entre ROS2 e Web

- **Status**: Accepted
- **Data**: 2026-06-17
- **Decisores**: Luiz Fernando de Freitas Oliveira
- **Contexto técnico**: Estratégia de comunicação entre o frontend web e o ecossistema ROS2

---

## Contexto

O frontend web (Express.js + HTML) precisa consumir dados dos tópicos ROS2 em tempo real (frequência cardíaca, frequência respiratória, heatmaps, etc.) para exibi-los na interface de monitoramento.

Existem duas abordagens principais para integrar uma aplicação web ao ROS2:

1. **Direta**: utilizar uma biblioteca como `rclnodejs` para conectar o processo Node.js diretamente ao DDS como um nó ROS2.
2. **Por bridge**: utilizar o `rosbridge_suite`, que expõe um servidor WebSocket (`rosbridge_server`) ao qual qualquer cliente web pode se conectar usando a biblioteca JavaScript `roslib.js`.

O projeto originalmente tinha `rclnodejs` listado como dependência no `web/package.json`, mas **não era utilizado em nenhum arquivo do backend**. A comunicação real com o ROS2 já ocorria via WebSocket do rosbridge no lado do cliente (browser).

## Decisão

Manter e formalizar o uso do **`rosbridge_suite`** como a única camada de integração entre o frontend web e os tópicos ROS2, executado como um serviço independente (`rosbridge`) no Docker Compose. A dependência `rclnodejs` foi **removida** do `web/package.json`.

A comunicação no frontend ocorre inteiramente via **`roslib.js`** (browser-side), que abre uma conexão WebSocket com `ws://localhost:9090`.

## Alternativas Consideradas

| Alternativa | Motivo de descarte |
|---|---|
| **`rclnodejs` no backend Node.js** | Requer compilação de extensões nativas C++ (`int64-napi`), incompatível com Alpine Linux sem build tools. Aumenta drasticamente o tamanho da imagem Docker e a complexidade do build. Além disso, obrigaria o servidor web a ser também um nó ROS2, misturando responsabilidades. |
| **gRPC-Web** | Introduz complexidade de infraestrutura (proxy Envoy ou similar) sem benefício claro frente ao WebSocket + JSON já suportado pelo `roslib.js`. |
| **MQTT Bridge** | Requer um broker MQTT adicional e bibliotecas de serialização customizadas para tipos de mensagens ROS2. |

## Consequências

### Positivas
- **Separação de responsabilidades clara**: o servidor web (`web`) é responsável apenas por servir HTML/CSS/JS e gerenciar dados de pacientes via MongoDB. O acesso ao ROS2 é feito pelo browser diretamente via WebSocket.
- **Serviço isolado e reiniciável**: o `rosbridge` pode ser reiniciado independentemente dos nós de processamento sem afetar o servidor web.
- **Zero dependência nativa no build do Node.js**: a remoção do `rclnodejs` eliminou erros de compilação (`int64-napi`) e reduziu o tamanho da imagem web de ~450MB para ~180MB.
- **Compatibilidade universal**: qualquer cliente com suporte a WebSocket (browser, Jupyter, scripts Python com `roslibpy`) pode consumir os dados.

### Negativas / Trade-offs
- O cliente browser precisa ter **acesso de rede direto ao rosbridge** na porta `9090`. Em deployments atrás de um proxy reverso (ex: nginx), seria necessário configurar o proxy para suportar upgrade de conexão WebSocket.
- A URL do rosbridge (`ws://localhost:9090`) está atualmente hardcoded no arquivo `rosControllerMonitoring.js`. Em ambientes com IPs diferentes (ex: acesso remoto ao laboratório), isso precisaria ser configurado.

## Links Relacionados
- [ADR-0001](./ADR-0001-docker-compose-para-orquestracao.md) — Adoção do Docker Compose
- [ADR-0003](./ADR-0003-host-networking-para-ros2-dds.md) — Host Networking para ROS2 DDS
