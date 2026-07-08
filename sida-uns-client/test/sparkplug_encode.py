"""Minimal Sparkplug B payload builder for the acceptance test.

Uses the SAME sparkplug_b.proto contract the client reads (compiled to
sparkplug_b_pb2 by run.sh via grpc_tools.protoc). It only ENCODES simulated
device messages; it never changes the schema.
"""
import time
import sparkplug_b_pb2 as spb

# Sparkplug B DataType enum (subset).
INT32 = 3
INT64 = 4
DOUBLE = 10
BOOLEAN = 11
STRING = 12


def _now_ms():
    return int(time.time() * 1000)


def _apply_value(metric, datatype, value):
    metric.datatype = datatype
    if value is None:
        metric.is_null = True
        return
    if datatype == DOUBLE:
        metric.double_value = float(value)
    elif datatype in (INT32,):
        metric.int_value = int(value)
    elif datatype in (INT64,):
        metric.long_value = int(value)
    elif datatype == BOOLEAN:
        metric.boolean_value = bool(value)
    elif datatype == STRING:
        metric.string_value = str(value)
    else:
        raise ValueError(f"unsupported datatype {datatype}")


def add_metric(payload, *, name=None, alias=None, datatype, value,
               eng_unit=None, timestamp=None):
    m = payload.metrics.add()
    if name is not None:
        m.name = name
    if alias is not None:
        m.alias = alias
    m.timestamp = timestamp if timestamp is not None else _now_ms()
    _apply_value(m, datatype, value)
    if eng_unit is not None:
        m.properties.keys.append("engUnit")
        pv = m.properties.values.add()
        pv.type = STRING
        pv.string_value = eng_unit
    return m


def new_payload(seq=0):
    p = spb.Payload()
    p.timestamp = _now_ms()
    p.seq = seq
    return p


def encode(payload):
    return payload.SerializeToString()


# ---- convenience builders matching SDD caso 1 --------------------------------

def nbirth(seq=0):
    p = new_payload(seq)
    # bdSeq is required by Sparkplug; the client ignores it.
    add_metric(p, name="bdSeq", datatype=INT64, value=0)
    add_metric(p, name="Node Control/Rebirth", datatype=BOOLEAN, value=False)
    return encode(p)


def dbirth(seq=1):
    p = new_payload(seq)
    add_metric(p, name="Temperature", alias=1, datatype=DOUBLE, value=60.5,
               eng_unit="°C")
    add_metric(p, name="Running", alias=2, datatype=BOOLEAN, value=True)
    return encode(p)


def ddata_temp(value, seq, use_alias=True):
    p = new_payload(seq)
    if use_alias:
        add_metric(p, alias=1, datatype=DOUBLE, value=value)
    else:
        add_metric(p, name="Temperature", datatype=DOUBLE, value=value)
    return encode(p)


def ddata_running(value, seq):
    p = new_payload(seq)
    add_metric(p, alias=2, datatype=BOOLEAN, value=value)
    return encode(p)


def ndeath():
    p = new_payload(0)
    add_metric(p, name="bdSeq", datatype=INT64, value=0)
    return encode(p)
