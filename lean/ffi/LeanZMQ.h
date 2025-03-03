#ifndef LEANZMQ_H
#define LEANZMQ_H

#ifdef __cplusplus
extern "C"
{
#endif

    void lean_zmq_init(void);
    void *lean_zmq_socket(int socket_type);
    int lean_zmq_close(void *socket);
    int lean_zmq_bind(void *socket, const char *endpoint);
    int lean_zmq_connect(void *socket, const char *endpoint);
    int lean_zmq_set_rcvtimeo(void *socket, int timeout_ms);
    int lean_zmq_send(void *socket, const char *msg);
    char *lean_zmq_recv(void *socket);
    void lean_zmq_free(char *ptr);

#ifdef __cplusplus
}
#endif

#endif
