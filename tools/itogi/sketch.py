import re,sys
FIL='''<filter id="r1" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency=".018" numOctaves="3" seed="2" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="9" xChannelSelector="R" yChannelSelector="G" result="d"/>
<feTurbulence type="fractalNoise" baseFrequency=".035" numOctaves="4" seed="9" result="w"/><feColorMatrix in="w" type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  -.28 0 0 0 1.08" result="wa"/><feComposite in="d" in2="wa" operator="in" result="dw"/>
<feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="4" result="g"/><feColorMatrix in="g" type="matrix" values=".14 0 0 0 .87  .14 0 0 0 .87  .14 0 0 0 .87  0 0 0 0 1" result="gg"/><feBlend in="dw" in2="gg" mode="multiply" result="b"/><feComposite in="b" in2="dw" operator="in"/></filter>
<filter id="r2" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency=".03" numOctaves="2" seed="7" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="6" xChannelSelector="R" yChannelSelector="G"/></filter>
<style>.sk *:not([stroke]){stroke:#33262F;stroke-width:3.2px;stroke-linejoin:round}.sk .noink *,.sk g{stroke:none}.sk g:not(.noink) *:not([stroke]){stroke:#33262F}.sk .noink *{stroke:none !important}</style>'''
MAP={"#3A2420":"#6A4434","#2A1C18":"#55352A","#433649":"#544A6E","#F2C14E":"#D9A441","#C9705A":"#B5584A","#7A3E5A":"#7A4A62","#8D4A69":"#8B5A72","#4B5D8C":"#5F7397","#3B2547":"#433649","#E7A94F":"#D9A441","#F6D58E":"#EDCB82","#E7BC6A":"#D9AE62","#D88B6F":"#C9806A","#5C7FA3":"#7D93B2","#B5584A":"#A84E40","#FFF1C9":"#C9913E","#FFF6E8":"#FBF3E6"}
NOINK=['<circle cx="-48" cy="4" r="12" fill="#E89A86" opacity=".6"/>','<circle cx="50" cy="4" r="12" fill="#E89A86" opacity=".6"/>']
def conv(src,dst,drop,extra=""):
    s=open(src,encoding='utf8').read()
    for d in drop: 
        assert d in s,d; s=s.replace(d,'')
    for k in NOINK: s=s.replace(k,k.replace('<','<g class="noink">',0)) if False else s.replace(k,'<g class="noink">'+k+'</g>')
    for a,b in MAP.items(): s=s.replace(a,b).replace(a.lower(),b)
    m=re.search(r'<defs>(.*?)</defs>',s,re.S);defs=m.group(1) if m else ''
    body=re.sub(r'<defs>.*?</defs>','',s,flags=re.S)
    body=re.sub(r'^.*?<svg[^>]*>','',body,flags=re.S).replace('</svg>','')
    out=f'<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920"><defs>{defs}{FIL}</defs>{extra}<g class="sk" filter="url(#r1)">{body}</g></svg>'
    open(dst,'w',encoding='utf8').write(out)
a=open('a.svg',encoding='utf8').read()
conv('a.svg','sa.svg',['<rect width="1080" height="1920" fill="#F4E4D0"/>','<path d="M0 1500 H1080 V1920 H0Z" fill="#E7CDB0"/>','<rect y="1560" width="1080" height="360" fill="#B98B6A"/>','<rect y="1560" width="1080" height="14" fill="#A57A5B"/>','<circle cx="880" cy="1180" r="300" fill="url(#glow)"/>','<ellipse cx="560" cy="1760" rx="470" ry="110" fill="none" stroke="#F4E4D0" stroke-width="8" stroke-dasharray="4 14"/>'])
conv('b.svg','sb.svg',['<rect width="1080" height="1920" fill="#DCD3EE"/>','<path d="M0 1780 Q300 1720 540 1760 T1080 1740 V1920 H0Z" fill="#9DB894"/>','<path d="M0 1840 Q360 1800 640 1830 T1080 1820 V1920 H0Z" fill="#8FA88A"/>'],'')
c=open('c.svg',encoding='utf8').read()
m=re.search(r'<circle cx="540" cy="1300" r="520" fill="url\(#mg\)"/>',c)
conv('c.svg','sc.svg',['<rect width="1080" height="1920" fill="#2B2F55"/>','<path d="M0 1500 Q300 1400 560 1460 T1080 1420 V1920 H0Z" fill="#353A68"/>',m.group(0),'<path d="M160 1760 q40 -30 80 -10 q20 -30 50 -20 q-14 16 -10 30 q40 6 60 30 q-40 0 -60 -10 q-40 20 -90 0 q-20 6 -30 -20z" fill="#232645"/>'])
