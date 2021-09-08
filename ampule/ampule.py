import io
import re

routes = []
variable_re = re.compile("^<([a-zA-Z]+)>$")

def _parse_headers(reader):
    headers = {}
    for line in reader:
        if line == b'\r\n': break
        header = str(line, "utf-8")
        title, content = header.split(":", 1)
        headers[title.strip().lower()] = content.strip()
    return headers

def _parse_params(path):
    query_string = path.split("?")[1] if "?" in path else ""
    param_list = query_string.split("&")
    params = {}
    for param in param_list:
        key_val = param.split("=")
        if len(key_val) == 2:
            params[key_val[0]] = key_val[1]
    return params

def _parse_body(reader):
    data = ""
    for line in reader:
        if line == b'\r\n': break
        data += str(line, "utf-8")
    return data

def _read_request(client):
    try:
        client.setblocking(False)
        buffer = bytearray(1024)
        client.recv_into(buffer)
        reader = io.BytesIO(buffer)
    except OSError:
        return None

    line = str(reader.readline(), "utf-8")
    (method, full_path, version) = line.rstrip("\r\n").split(None, 2)

    path = full_path.split("?")[0]
    params = _parse_params(full_path)
    headers = _parse_headers(reader)
    data = _parse_body(reader)

    return (method, path, params, headers, data)

def _send_response(client, code, headers, data):
    response = "HTTP/1.1 %i\r\n" % code

    headers["Server"] = "ESP32Server"
    headers["Connection"] = "Close"
    headers["Access-Control-Allow-Origin"] = '*'
    headers["Access-Control-Allow-Methods"] = 'GET, POST'
    headers["Access-Control-Allow-Headers"] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'
    for k, v in headers.items():
        response += "%s: %s\r\n" % (k, v)

    response += "\r\n"
    response += str(data, "utf-8")
    response += "\r\n"

    print("Response:", response)
    client.send(response)
    client.close()

def _on_request(rule, request_handler):
    regex = "^"
    rule_parts = rule.split("/")
    for part in rule_parts:
        var = variable_re.match(part)
        if var:
            regex += r"([a-zA-Z0-9_-]+)\/"
        else:
            regex += part + r"\/"
    regex += "?$"
    routes.append(
        (re.compile(regex), {"func": request_handler})
    )

def _match_route(path):
    for matcher, route in routes:
        match = matcher.match(path)
        if match:
            return (match.groups(), route)
    return None

def listen(socket):
    client, remote_address = socket.accept()
    request = _read_request(client)
    if request:
        (method, path, params, headers, data) = request
        match = _match_route(path)
        if match:
            args, route = match
            status, headers, body = route["func"](request, *args)
            _send_response(client, status, headers, body)

def route(rule):
    return lambda func: _on_request(rule, func)