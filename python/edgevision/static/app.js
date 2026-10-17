const $=(id)=>document.getElementById(id);
const canvas=$("plane"),ctx=canvas.getContext("2d");
const colors=["#68dbc0","#f4c778","#95acff","#eaa1d4"];
let lastEvent=null,lastReceived=0;
function draw(event){
  ctx.clearRect(0,0,canvas.width,canvas.height);
  ctx.strokeStyle="#1c2b31";ctx.lineWidth=1;
  for(let x=0;x<1280;x+=80){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,720);ctx.stroke();}
  for(let y=0;y<720;y+=80){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(1280,y);ctx.stroke();}
  if(!event)return;
  for(const [i,obj] of event.objects.entries()){
    const b=obj.bbox,x=b.left/event.width*1280,y=b.top/event.height*720,w=b.width/event.width*1280,h=b.height/event.height*720;
    ctx.strokeStyle=colors[i%colors.length];ctx.fillStyle=colors[i%colors.length]+"15";ctx.lineWidth=3;
    ctx.fillRect(x,y,w,h);ctx.strokeRect(x,y,w,h);
    ctx.fillStyle=colors[i%colors.length];ctx.font="18px system-ui";ctx.fillText(obj.label+" "+Math.round(obj.confidence*100)+"%",x+5,Math.max(22,y-8));
  }
}
function update(event){
  lastEvent=event;lastReceived=Date.now();
  $("source").textContent=event.source_id;$("count").textContent=event.objects.length;
  $("frame").textContent=event.frame_id;$("mode").textContent=event.simulated?"SIMULATED":"DEVICE EVENTS";
  $("live").textContent=event.simulated?"SYNTHETIC METADATA":"DEVICE METADATA";
  $("note").textContent=event.simulated?"Simulator is active. Boxes are generated; no inference or video is running.":"Device events received. This plane shows coordinates, not camera video.";
  const rows=event.objects.map((obj)=>{
    const row=document.createElement("div");row.className="object";
    const dot=document.createElement("i"),label=document.createElement("div"),name=document.createElement("strong"),detail=document.createElement("small"),score=document.createElement("b");
    name.textContent=obj.label;detail.textContent="Class "+obj.class_id;score.textContent=Math.round(obj.confidence*100)+"%";
    label.append(name,detail);row.append(dot,label,score);return row;
  });
  if(!rows.length){const p=document.createElement("p");p.className="empty";p.textContent="No objects in this frame.";rows.push(p);}
  $("objects").replaceChildren(...rows);draw(event);
}
function connect(){
  const socket=new WebSocket((location.protocol==="https:"?"wss://":"ws://")+location.host+"/ws");
  socket.onopen=()=>{$("connection").textContent="● Connected";};
  socket.onmessage=(message)=>{try{update(JSON.parse(message.data));}catch{$("connection").textContent="Invalid event received";}};
  socket.onerror=()=>socket.close();
  socket.onclose=()=>{$("connection").textContent="Disconnected · retrying";setTimeout(connect,2000);};
}
draw(null);connect();
setInterval(()=>{if(lastEvent&&Date.now()-lastReceived>5000)$("live").textContent="STALE · NO RECENT EVENTS";},1000);
