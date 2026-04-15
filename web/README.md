# AIMS Interface

**AIMS Interface** fornece um sistema em plataforma web para controlar o sistema que faz uso do [ROS2](https://docs.ros.org/en/foxy/).

Dentre as funcionalidades estão CRUD de _Pacientes_ e a possibilidade de capturar os sinais vitais dos _Pacientes_.

## O sistema

O sistema web é baseado em Express.js para implementar os endpoints. Faz uso da biblioteca [roslibjs](http://wiki.ros.org/roslibjs) diretamente no client-side para se comunicar com o sistema ROS. 

## Banco de dados

[MongoDB](https://www.mongodb.com/) é o banco de dados utilizado. O sistema não inicia se não tiver conexão com o banco.

Se estiver conectando com um banco de dados novo, será necessário [criar](https://databasefaqs.com/create-tables-in-mongodb/) uma nova _Collection_ chamada "patients".

A _string_ de conexão e lida por variáveis de ambiente:

- `DB_CONNECTION_STRING_LOCAL`
- `DB_CONNECTION_STRING_PROD`

O banco padrao atualmente configurado no codigo esta definido no arquivo `app.js`.

###### *Caso esteja rodando uma instância local do MongoDB e encontre problemas ao iniciar ele, cheque [este tópico](https://stackoverflow.com/questions/9884233/mongodb-service-is-not-starting-up)

## Instalação

Clone o repositório e baixe as dependências do projeto com:

```bash
cd web
npm install
```

### Demais dependências

É necessário ter tanto o ambiente ROS2 devidamente instalado, quanto o [Rosbridge server](http://wiki.ros.org/rosbridge_server).

Instale o Rosbridge server com o comando (substitua '<ROS_DISTRO>' pela distribuição utilizada (atualmente é a foxy):

```bash
sudo apt install ros-<ROS_DISTRO>-rosbridge-server
```

Na dúvida, realize o source do environment novamente (considere o mesmo '<ROS_DISTRO>' utilizado anteriormente):

```bash
source /opt/ros/<ROS_DISTRO>/setup.bash
```



## Inicialização

Primeiramente, rode o Rosbridge com o comando:

```bash
ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```

Ocorrendo tudo certo, uma saída do comando acima esperada seria:

```
[INFO] [launch]: All log files can be found below /home/tatuapu/.ros/log/2023-02-24-10-14-44-518595-Destruction-33337
[INFO] [launch]: Default logging verbosity is set to INFO
[INFO] [rosbridge_websocket-1]: process started with pid [33338]
[INFO] [rosapi_node-2]: process started with pid [33340]
[rosbridge_websocket-1] [INFO] [1677244488.606492483] [rosbridge_websocket]: Rosbridge WebSocket server started on port 9090
[rosbridge_websocket-1] [INFO] [1677244499.941333337] [rosbridge_websocket]: Client connected. 1 clients total.

```


Após possuir uma instância do banco de dados rodando, inicie a aplicação web com:

```bash
npm run dev
```

Esse comando executa `node app.js development`.

Ocorrendo tudo certo, uma saída do comando acima esperada seria:

```
Server started at 3001

```

Assim, o sistema estará disponível no [localhost](http://localhost:3001).

## Execução integrada com ROS2

No fluxo completo do projeto, o launch do ROS2 ([aims_launch.py](../aims_ws/src/csi/launch/aims_launch.py)) já inicia a aplicação web automaticamente.
