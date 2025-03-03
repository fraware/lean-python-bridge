import zmq
import json
import logging
import numpy as np
from validation import validate_matrix_model

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO
)


def main():
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5555")
    logging.info("ZeroMQ REP Server bound at tcp://*:5555")

    while True:
        try:
            msg = socket.recv_string()
            logging.info(f"Received request: {msg}")
        except Exception as e:
            logging.error(f"Error receiving message: {str(e)}")
            continue

        try:
            data = json.loads(msg)
            validate_matrix_model(data)
        except Exception as e:
            logging.error(f"Validation or JSON error: {str(e)}")
            socket.send_string(json.dumps({"status": "error", "message": str(e)}))
            continue

        matrix = data["matrix"]
        np_mat = np.array(matrix)
        sum_val = float(np_mat.sum())

        resp = {
            "status": "success",
            "matrix_sum": sum_val,
            "model_checked": data["model"]["name"],
            "schema_version_used": data["schema_version"],
        }
        socket.send_string(json.dumps(resp))
        logging.info(f"Reply sent: {resp}")


if __name__ == "__main__":
    main()
