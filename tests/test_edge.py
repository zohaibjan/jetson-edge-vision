import asyncio
import json
from pathlib import Path
import pytest
import zmq
import zmq.asyncio
from fastapi.testclient import TestClient
from edgevision.bridge import Hub, TOPIC, create_app, subscribe
from edgevision.config import build_config
from edgevision.simulator import event

def test_valid_event_and_bounded_fanout():
    hub=Hub()
    queue=asyncio.Queue(maxsize=2)
    hub.clients.add(queue)
    for n in range(4):
        assert hub.ingest([TOPIC,json.dumps(event(n)).encode()])
    assert queue.qsize()==2 and hub.dropped==2
    assert queue.get_nowait()["frame_id"]==2

@pytest.mark.parametrize("mutate",[
    lambda x:x.update(width=0),
    lambda x:x.update(objects=x["objects"]*50),
    lambda x:x["objects"][0].update(confidence=2),
    lambda x:x["objects"][0]["bbox"].update(left=-1),
    lambda x:x.update(simulated="not-a-bool"),
])
def test_rejects_invalid_metadata(mutate):
    value=event(1);mutate(value)
    hub=Hub()
    assert not hub.ingest([TOPIC,json.dumps(value).encode()])
    assert hub.rejected==1

def test_bad_multipart_and_oversize():
    hub=Hub()
    for parts in ([b"wrong",b"{}"],[TOPIC,b"{"],[TOPIC,b"x"*262145],[TOPIC,b"{}",b"extra"]):
        assert not hub.ingest(parts)

def test_model_cache_invalidation(tmp_path):
    model=tmp_path/"model.onnx";model.write_bytes(b"synthetic model bytes")
    labels=tmp_path/"labels.txt";labels.write_text("person\nvehicle\n")
    parser=tmp_path/"parser.so";parser.write_bytes(b"synthetic parser bytes")
    a,engine=build_config(model,labels,parser,tmp_path/"cache","board-a-trt-10")
    b,_=build_config(model,labels,parser,tmp_path/"cache","board-b-trt-10")
    assert a!=b and str(engine) in a.read_text()
    model.write_bytes(b"changed")
    c,_=build_config(model,labels,parser,tmp_path/"cache","board-a-trt-10")
    assert a!=c
    parser.write_bytes(b"new parser")
    d,_=build_config(model,labels,parser,tmp_path/"cache","board-a-trt-10")
    assert c!=d

def test_rejects_pt_and_missing_runtime(tmp_path):
    for model,runtime in ((tmp_path/"a.pt","runtime"),(tmp_path/"a.onnx","")):
        with pytest.raises(ValueError):
            build_config(model,tmp_path/"labels",tmp_path/"parser",tmp_path,runtime)

def test_http_and_cross_origin_websocket():
    with TestClient(create_app()) as client:
        assert client.get("/").status_code==200
        assert client.get("/health").json()["events"]==0
        assert client.get("/",headers={"host":"attacker.invalid"}).status_code==400
        with pytest.raises(Exception):
            with client.websocket_connect("/ws",headers={"origin":"https://attacker.invalid"}):
                pass

def test_real_zeromq_to_subscriber():
    async def run():
        context=zmq.asyncio.Context()
        pub=context.socket(zmq.XPUB)
        pub.setsockopt(zmq.LINGER,0)
        endpoint="inproc://edge-regression"
        pub.bind(endpoint)
        hub=Hub()
        task=asyncio.create_task(subscribe(endpoint,hub,context))
        try:
            # Wait for the XPUB subscription notification, not a guessed sleep.
            for _ in range(100):
                try:
                    note=await pub.recv(zmq.DONTWAIT)
                    if note==b"\x01"+TOPIC:
                        break
                except zmq.Again:
                    pass
                await asyncio.sleep(.01)
            else:
                pytest.fail("No subscriber joined")
            await pub.send_multipart([TOPIC,json.dumps(event(42)).encode()])
            for _ in range(100):
                if hub.accepted:
                    break
                await asyncio.sleep(.01)
            assert hub.last["frame_id"]==42 and hub.last["simulated"] is True
        finally:
            task.cancel()
            await asyncio.gather(task,return_exceptions=True)
            pub.close();context.term()
    asyncio.run(run())

def test_websocket_delivers_validated_frame():
    app = create_app()
    with TestClient(app) as client:
        with client.websocket_connect("/ws", headers={"origin":"http://testserver"}) as websocket:
            assert client.portal.call(app.state.hub.ingest, [TOPIC, json.dumps(event(73)).encode()])
            frame = websocket.receive_json()
            assert frame["schema"] == "edge.detections.v1"
            assert frame["frame_id"] == 73 and frame["simulated"] is True
