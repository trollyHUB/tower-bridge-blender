"""Additional carved stonework, riveted steel and practical-light fixtures."""
def build(g):
    box,beam,cyl,group=(g[k] for k in ['box','beam','cyl','group'])
    trim,stone,blue,gold=(g[k] for k in ['trim','stone','blue','gold'])
    for tx in [-39,39]:
        group('Tower carved corbels '+str(tx),'Architecture | carved details')
        for y in [-12.35,12.35]:
            for dx in [-6.8,-4.5,-2.25,0,2.25,4.5,6.8]:
                box((tx+dx,y,49.15),(.45,.65,1.15),trim)
                box((tx+dx,y,48.6),(.27,.43,.2),stone)
            for dx in [-7.2,7.2]:
                box((tx+dx,y,30),(1.0,.45,7),trim)
                for z in [27,29,31,33]:box((tx+dx,y-.1, z),(1.15,.6,.15),stone)
        for yy in [-12.3,12.3]:
            cyl((tx,yy,39.4),.9,.16,gold,24,axis=(0,1,0))
            box((tx,yy+(-.12 if yy<0 else .12),39.4),(.17,.10,1.1),blue)
        # Rivets along existing steel side plates; never project into road lanes.
        group('Tower riveted steel '+str(tx),'Architecture | steel details')
        for y in [-8.8,8.8]:
            for x in [tx-7,tx-5,tx-3,tx+3,tx+5,tx+7]:
                cyl((x,y,10.8),.075,.12,gold,8,axis=(0,1,0))
    group('Dock lamp fixtures','Architecture | practical fixtures')
    for sign in [-1,1]:
        for y in [29,41]:g['lamp'](sign*103,y,1.2)
    group('Walkway strip diffusers','Architecture | practical fixtures')
    for y in [-7.9,7.9]:box((0,y,43.0),(56,.18,.09),g['lampmat'])
    group('Cafe string lights','Architecture | practical fixtures')
    for x in [-151,-143]:
        beam((x-2,19,10.2),(x-2,19,14.3),.075,blue)
        beam((x-2,19,14.3),(x+2,19,14.3),.035,gold)
        for dx in [-1.5,-.5,.5,1.5]:g['sphere']((x+dx,19,14.1),.10,g['lampmat'])
