# Uso: python3 scripts/marcador.py entrada.glb salida.glb x z  (en metros, ejes glTF)
# Añade en el suelo, bajo (x, z), un anillo blanco y una onda que se expande.
import sys,json,struct,math
src,dst=sys.argv[1:3]; X,Z=map(float,sys.argv[3:5])
d=open(src,'rb').read(); l=struct.unpack('<I',d[12:16])[0]; j=json.loads(d[20:20+l])
bl=struct.unpack('<I',d[20+l:24+l])[0]; B=bytearray(d[28+l:28+l+bl])

def add(data,fmt,count,typ,target=None,minmax=False):
    B.extend(b'\0'*(-len(B)%4)); off=len(B)
    flat=[x for v in data for x in (v if isinstance(v,(list,tuple)) else [v])]
    B.extend(struct.pack('<%d%s'%(len(flat),fmt),*flat))
    bv={'buffer':0,'byteOffset':off,'byteLength':len(B)-off}
    if target: bv['target']=target
    j['bufferViews'].append(bv)
    acc={'bufferView':len(j['bufferViews'])-1,'componentType':5126 if fmt=='f' else 5125,'count':count,'type':typ}
    if minmax:
        n={'SCALAR':1,'VEC3':3}[typ]; cols=[[v[i] for v in data] if n>1 else data for i in range(n)]
        acc['min']=[min(c) for c in cols] if n>1 else [min(data)]; acc['max']=[max(c) for c in cols] if n>1 else [max(data)]
    j['accessors'].append(acc); return len(j['accessors'])-1

def mesh(name,pos,nrm,idx,mat):
    p=add(pos,'f',len(pos),'VEC3',34962,True); n=add(nrm,'f',len(nrm),'VEC3',34962)
    i=add(idx,'I',len(idx),'SCALAR',34963)
    j['meshes'].append({'name':name,'primitives':[{'attributes':{'POSITION':p,'NORMAL':n},'indices':i,'material':mat}]})
    return len(j['meshes'])-1

def ring(r0,r1,y,seg=128):
    pos=[];idx=[]
    for k in range(seg):
        a=2*math.pi*k/seg; c,s=math.cos(a),math.sin(a)
        pos+=[(r0*c,y,r0*s),(r1*c,y,r1*s)]
        a0,a1,b0,b1=2*k,2*k+1,(2*k+2)%(2*seg),(2*k+3)%(2*seg)
        idx+=[a0,b0,a1,a1,b0,b1]
    return pos,[(0,1,0)]*len(pos),idx


mats=j['materials']
mats.append({'name':'marcador','doubleSided':True,'emissiveFactor':[1,1,1],
             'alphaMode':'BLEND','pbrMetallicRoughness':{'baseColorFactor':[1,1,1,0.1],'metallicFactor':0,'roughnessFactor':1}})
m_ring=len(mats)-1

R=0.6
nodes=j['nodes']
def node(**kw): nodes.append(kw); return len(nodes)-1
n_ring=node(name='marcador_anillo',mesh=mesh('marcador_anillo',*ring(R-0.04,R,0.003),m_ring))
n_onda=node(name='marcador_onda',mesh=mesh('marcador_onda',*ring(R-0.02,R,0.004),m_ring))
n_root=node(name='marcador',translation=[X,0,Z],children=[n_ring,n_onda])
j['scenes'][0]['nodes'].append(n_root)

# Onda: crece de 0,3 a 2,2 veces el anillo en el 90 % del periodo y desaparece hasta el siguiente
anim=j['animations'][0]; ins={s['input'] for s in anim['samplers']}
t0=min(j['accessors'][i]['min'][0] for i in ins); t1=max(j['accessors'][i]['max'][0] for i in ins)
cycles=max(1,round((t1-t0)/2.0)); P=(t1-t0)/cycles
times=[];scales=[]
for c in range(cycles):
    b=t0+c*P
    for t,s in ((b,0.3),(b+0.9*P,2.2),(b+0.9*P+0.001,0.0),(b+P-0.001,0.0)):
        times.append(t); scales.append((s,1,s))
times.append(t1); scales.append((0.3,1,0.3))
ti=add(times,'f',len(times),'SCALAR',None,True); so=add(scales,'f',len(scales),'VEC3')
anim['samplers'].append({'input':ti,'output':so,'interpolation':'LINEAR'})
anim['channels'].append({'sampler':len(anim['samplers'])-1,'target':{'node':n_onda,'path':'scale'}})

B.extend(b'\0'*(-len(B)%4)); j['buffers'][0]['byteLength']=len(B)
js=json.dumps(j,separators=(',',':')).encode(); js+=b' '*(-len(js)%4)
open(dst,'wb').write(b'glTF'+struct.pack('<II',2,28+len(js)+len(B))+struct.pack('<I',len(js))+b'JSON'+js+struct.pack('<I',len(B))+b'BIN\0'+bytes(B))
print('OK',dst,'onda: %d ciclos de %.2f s'%(cycles,P))
