#include <zmq.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

// Production note: For concurrency, each thread must create its own ZeroMQ socket.
// Sockets are not thread-safe. If needed, use separate contexts or advanced patterns.

static void *global_ctx = NULL;

// Helper: log with timestamp
static void log_msg(const char *msg)
{
    time_t now = time(NULL);
    struct tm *t = localtime(&now);
    char buffer[64];
    strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M:%S", t);
    fprintf(stderr, "[C-FFI] %s | %s\n", buffer, msg);
}

void lean_zmq_init(void)
{
    if (global_ctx == NULL)
    {
        global_ctx = zmq_ctx_new();
        if (global_ctx == NULL)
        {
            log_msg("Error: Failed to create ZMQ context (NULL).");
        }
        else
        {
            log_msg("ZMQ context created (global_ctx).");
        }
    }
}

void *lean_zmq_socket(int socket_type)
{
    if (global_ctx == NULL)
    {
        lean_zmq_init();
    }
    void *sock = zmq_socket(global_ctx, socket_type);
    if (!sock)
    {
        log_msg("Error: zmq_socket returned NULL.");
    }
    else
    {
        log_msg("ZMQ socket created.");
    }
    return sock;
}

int lean_zmq_close(void *socket)
{
    if (!socket)
    {
        log_msg("Error: Attempt to close NULL socket.");
        return -1;
    }
    int rc = zmq_close(socket);
    if (rc != 0)
    {
        log_msg("Error: zmq_close failed.");
    }
    else
    {
        log_msg("ZMQ socket closed successfully.");
    }
    return rc;
}

int lean_zmq_bind(void *socket, const char *endpoint)
{
    if (!socket || !endpoint)
    {
        log_msg("Error: Null socket or endpoint in zmq_bind.");
        return -1;
    }
    int rc = zmq_bind(socket, endpoint);
    if (rc != 0)
    {
        log_msg("Error: zmq_bind failed.");
    }
    else
    {
        char msg[256];
        snprintf(msg, sizeof(msg), "ZMQ socket bound to endpoint: %s", endpoint);
        log_msg(msg);
    }
    return rc;
}

int lean_zmq_connect(void *socket, const char *endpoint)
{
    if (!socket || !endpoint)
    {
        log_msg("Error: Null socket or endpoint in zmq_connect.");
        return -1;
    }
    int rc = zmq_connect(socket, endpoint);
    if (rc != 0)
    {
        log_msg("Error: zmq_connect failed.");
    }
    else
    {
        char msg[256];
        snprintf(msg, sizeof(msg), "ZMQ socket connected to endpoint: %s", endpoint);
        log_msg(msg);
    }
    return rc;
}

// Example to set RCVTIMEO for blocking receive with a timeout
int lean_zmq_set_rcvtimeo(void *socket, int timeout_ms)
{
    if (!socket)
    {
        log_msg("Error: Null socket in set_rcvtimeo.");
        return -1;
    }
    int rc = zmq_setsockopt(socket, ZMQ_RCVTIMEO, &timeout_ms, sizeof(timeout_ms));
    if (rc != 0)
    {
        log_msg("Error: zmq_setsockopt (RCVTIMEO) failed.");
    }
    else
    {
        char buf[128];
        sprintf(buf, "ZMQ RCVTIMEO set to %d ms.", timeout_ms);
        log_msg(buf);
    }
    return rc;
}

int lean_zmq_send(void *socket, const char *msg)
{
    if (!socket || !msg)
    {
        log_msg("Error: Null socket or msg in zmq_send.");
        return -1;
    }
    int rc = zmq_send(socket, msg, strlen(msg), 0);
    if (rc < 0)
    {
        log_msg("Error: zmq_send failed.");
    }
    else
    {
        log_msg("ZMQ message sent successfully.");
    }
    return rc;
}

/*
   lean_zmq_recv
   -------------
   Returns a pointer to a newly malloc'd buffer containing the message.
   If there's a timeout or error, returns NULL.
*/
char *lean_zmq_recv(void *socket)
{
    if (!socket)
    {
        log_msg("Error: Null socket in zmq_recv.");
        return NULL;
    }
    char buffer[4096];
    memset(buffer, 0, sizeof(buffer));

    int bytes = zmq_recv(socket, buffer, sizeof(buffer) - 1, 0);
    if (bytes < 0)
    {
        log_msg("Warning: zmq_recv timed out or failed.");
        return NULL;
    }
    buffer[bytes] = '\0';

    // Allocate a new char* to hold the message, which Lean must eventually free
    char *result = (char *)malloc(bytes + 1);
    if (!result)
    {
        log_msg("Error: Out of memory in lean_zmq_recv.");
        return NULL;
    }
    strcpy(result, buffer);

    log_msg("ZMQ message received successfully.");
    return result;
}

/*
   lean_zmq_free
   -------------
   Frees the buffer allocated by lean_zmq_recv. Lean must call this
   once it has copied the data into a Lean String or ByteArray.
*/
void lean_zmq_free(char *ptr)
{
    if (ptr)
    {
        free(ptr);
        log_msg("Freed ZMQ receive buffer.");
    }
}
