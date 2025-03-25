# Mensagens Recorrentes

O GYM NATION Bot permite configurar mensagens que serão enviadas automaticamente em intervalos regulares. Esta funcionalidade é útil para lembretes periódicos, motivação diária, ou qualquer mensagem que precise ser repetida regularmente.

## Comandos Disponíveis

### 1. Configurar uma Mensagem Recorrente

```
/sayrecurrent <intervalo> <mensagem>
```

**Parâmetros:**
- `<intervalo>`: Tempo entre cada envio da mensagem
- `<mensagem>`: Texto que será enviado periodicamente

**Formatos de intervalo aceitos:**
- `30m` - 30 minutos
- `1h` - 1 hora
- `1h30m` - 1 hora e 30 minutos
- `30` - 30 minutos (sem unidade assume minutos)

**Exemplos:**
```
/sayrecurrent 30m Lembrete para beber água!
/sayrecurrent 1h Hora de fazer uma pausa e se alongar!
/sayrecurrent 1h30m Não se esqueça de registrar sua alimentação!
/sayrecurrent 24h Bom dia, pessoal! Vamos treinar hoje?
```

### 2. Listar Mensagens Recorrentes

```
/listrecurrent
```

Este comando mostra todas as mensagens recorrentes configuradas para o chat atual. Para cada mensagem, são exibidas as seguintes informações:
- ID da mensagem (necessário para desativar)
- Texto da mensagem
- Intervalo de repetição
- Quem adicionou a mensagem
- Data de criação
- Data do último envio

### 3. Desativar uma Mensagem Recorrente

```
/delrecurrent <id_da_mensagem>
```

**Parâmetros:**
- `<id_da_mensagem>`: ID da mensagem recorrente que deseja desativar

O ID da mensagem pode ser obtido com o comando `/listrecurrent`.

## Comportamento e Funcionamento

### Agendamento de Mensagens

- Quando uma mensagem recorrente é configurada, ela será enviada pela primeira vez após o intervalo completo a partir do momento da configuração.
- Por exemplo, se você configurar uma mensagem para ser enviada a cada 1 hora, a primeira mensagem será enviada 1 hora após a configuração.

### Formato das Mensagens

As mensagens recorrentes são enviadas com o seguinte formato:
```
🟢 MENSAGEM RECORRENTE 🟢

[Texto da mensagem]

-------------------------------------
```

### Persistência

- As mensagens recorrentes são armazenadas no banco de dados MongoDB.
- Se o bot for reiniciado, todas as mensagens recorrentes ativas serão carregadas e reagendadas automaticamente.
- As mensagens desativadas permanecem no banco de dados, mas não são mais enviadas.

### Limitações

- Não há limite para o número de mensagens recorrentes que podem ser configuradas.
- O intervalo mínimo é de 1 minuto.
- O intervalo máximo não tem limite teórico, mas recomenda-se não exceder 1 mês (720 horas).

## Casos de Uso

1. **Lembretes de hidratação**: Configurar mensagens a cada 30 minutos lembrando os membros do grupo para beber água.
2. **Motivação diária**: Enviar uma mensagem motivacional todos os dias pela manhã.
3. **Lembretes de treino**: Enviar lembretes em dias específicos da semana para treinos agendados.
4. **Dicas de nutrição**: Compartilhar dicas de nutrição periodicamente.
5. **Anúncios recorrentes**: Informar sobre eventos regulares ou regras do grupo.

## Solução de Problemas

- Se uma mensagem recorrente não estiver sendo enviada, verifique se ela está ativa usando `/listrecurrent`.
- Se o bot for removido do grupo, as mensagens recorrentes desse grupo serão interrompidas.
- Se o bot for adicionado novamente ao grupo, as mensagens recorrentes precisarão ser reconfiguradas.
- Apenas administradores podem configurar, listar e desativar mensagens recorrentes. 