#####################
#written by Frank Rueter
#last modified	Apr/20/2006
#		Apr/21/2006 - added per particle variations for size, speed and spread
#		Apr/24/2006 - added "inherit velocity" functionality
#		Apr/25/2006 - added preset functionality
#this is used by Particles.gizmo
#needs ObjVPos.tcl, SaveParticlePresets.tcl and LoadParticlePresets.tcl installed in Nuke's plugin location
#####################

proc GenerateParticles {} {
	set counter 1
	set NewNodes {}
	
	
	in this {
		#delete existing nodes
		foreach cur_node [nodes] {
			if {[knob $cur_node.label] == "auto generated"} {
				delete $cur_node
				}
			}
		
		#if ![ask "this will create [expression ([value this.stop]-[value this.start])*[value this.emission_rate]] particles."] {return}
		#generate new nodes #############################################################
		#for {set cur_time 0} {$cur_time < [llength [array names emitterSurface]]} {incr cur_time}
		if [knob this.use_emitter] {
			#set rate [expression ([knob this.stop]-[knob this.start])/[llength $emitterSurface]]
			set emitterSurface [ObjVPos [knob this.emitter_obj]]
			set rate 1
			} else {
			set rate [knob this.emission_rate]
			}
		for {set cur_time 0} {[expression [knob this.start]+$cur_time] < [knob this.stop]} {set cur_time [expression $cur_time+1/$rate]} {
			
			push 0
			#Multiply node, SCALE CURVES #############################################################
			Multiply -New
			set curNode [stack 0]
			addUserKnob node $curNode 20 Curves
			addUserKnob node $curNode 7 fade_in_curve l {fade in curve}
			addUserKnob node $curNode 7 fade_out_curve l {fade out curve}
			addUserKnob node $curNode 7 seed l seed
			addUserKnob node $curNode 7 local_time l {local time}
			addUserKnob node $curNode 7 grow_curve l {grow curve}
			addUserKnob node $curNode 7 shrink_curve l {shrink curve}
			knob $curNode.channels rgba
			knob $curNode.value {{this.fade_in_curve*this.fade_out_curve}}
			knob $curNode.label "auto generated"
			knob $curNode.fade_in_curve "{\"clamp( ( (frame-parent.start-$cur_time+1) / (1+parent.fade_in_for) ) )\"}"
			knob $curNode.fade_out_curve "{\"1-clamp( ( (frame-parent.start-$cur_time-parent.life_span+parent.fade_out_for+1) / (1+parent.fade_out_for) ) )\"}"
			knob $curNode.seed "{\"random ($cur_time,parent.size_seed)\"}"
			knob $curNode.local_time "{(frame-parent.start-$cur_time)/([value this.life_span]-1)}"
			knob $curNode.grow_curve "{\"clamp( ( (frame-parent.start-$cur_time+1) / (1+parent.grow_for) ) )\"}"
			knob $curNode.shrink_curve "{\"1-clamp( ( (frame-parent.start-$cur_time-parent.life_span+parent.shrink_for+1) / (1+parent.shrink_for) ) )\"}"
			input $curNode 0 img
			lappend NewNodes $curNode
			
			#VISIBILITY #############################################################
			
			switch [knob this.type] {
				sphere {
					Sphere -New
					set curNode [stack 0]
					knob $curNode.rows {{parent.resolution}}
					knob $curNode.columns {{this.rows.0}}
					knob $curNode.radius 0.1
					}
				cube {
					Cube -New
					set curNode [stack 0]
					knob $curNode.cube {-0.1 -0.1 -0.1 0.1 0.1 0.1}
					set cut_paste_input [stack 0]
					}
				cylinder {
					Cylinder -New
					set curNode [stack 0]
					knob $curNode.rows {{parent.resolution}}
					knob $curNode.columns {{this.rows.0}}
					knob $curNode.radius 0.1
					knob $curNode.height {{this.radius*2}}
					set cut_paste_input [stack 0]
					}
				obj {
					ReadGeo -New
					set curNode [stack 0]
					knob $curNode.file {[knob parent.obj_type]}
					set cut_paste_input [stack 0]
					}
				sprite {
					Card -New
					set curNode [stack 0]
					set cut_paste_input [stack 0]
					}					
									
				}
			knob $curNode.label "auto generated"
			knob $curNode.disable {{"!inrange (input.local_time,0,1)"}}
			lappend NewNodes $curNode
			
			#SPEED, ROTATION,SCALE #############################################################
			TransformGeo -New
			set curNode [stack 0]
			addUserKnob node $curNode 20 User
			addUserKnob node $curNode 7 seed l seed
			addUserKnob node $curNode 7 rot_seed l rot_seed
			knob $curNode.seed "{\"random ($cur_time,parent.speed_seed)\"}"
			knob $curNode.rot_seed "{\"random ($cur_time,parent.rotation_seed)\"}"
			knob $curNode.selectable false
			if ![knob this.use_emitter] {\
				knob $curNode.translate "\
				0\
				0\
				{\"\
				!input.disable * (\
				-parent.normCurve(frame-parent.start-$cur_time) *\
				(1+(random ($cur_time,this.seed)*2-1)*parent.speed_var) * (parent.speed)\
				)\"}\
				"} else {
				knob $curNode.translate.x [lindex [lindex $emitterSurface $cur_time] 0]
				knob $curNode.translate.y [lindex [lindex $emitterSurface $cur_time] 1]
				knob $curNode.translate.z [lindex [lindex $emitterSurface $cur_time] 2]
				}
			knob $curNode.rotate "\
				{\"!input.disable * parent.orientation.x -\
				parent.normCurve(frame-parent.start+$cur_time) *\
				(1+(random ($cur_time,this.rot_seed)*2-1)*parent.rotation_var) * parent.local_rot.x\"}\
				
				{\"!input.disable * parent.orientation.y -\
				parent.normCurve(frame-parent.start+$cur_time) *\
				(1+(random ($cur_time,this.rot_seed)*2-1)*parent.rotation_var) * parent.local_rot.y\"}\
				
				{\"!input.disable * parent.orientation.z -\
				parent.normCurve(frame-parent.start+$cur_time) *\
				(1+(random ($cur_time,this.rot_seed)*2-1)*parent.rotation_var) * parent.local_rot.z\"}\
				"
				
				
			knob $curNode.uniform_scale "{\"parent.size*input.input.grow_curve*input.input.shrink_curve + ((random($cur_time,input.input.seed)*2-1)*parent.size_var*parent.size)\"}"
			knob $curNode.label "auto generated"
			knob $curNode.name "LocalMotion_$counter"
			lappend NewNodes $curNode

			#SPREAD #############################################################
			TransformGeo -New
			set curNode [stack 0]
			addUserKnob node $curNode 20 User
			addUserKnob node $curNode 7 seed l seed
			knob $curNode.seed "{\"random ($cur_time,parent.spread_seed)\"}"
			knob $curNode.rot_order "YXZ"
			knob $curNode.translate "\
				{\"((1-parent.inherit_velocity)* parent.input1.translate.x(parent.normCurve($cur_time+parent.start)) + parent.inherit_velocity*parent.input1.translate.x)\"}\
				{\"((1-parent.inherit_velocity)* parent.input1.translate.y(parent.normCurve($cur_time+parent.start)) + parent.inherit_velocity*parent.input1.translate.y)\"}\
				{\"((1-parent.inherit_velocity)* parent.input1.translate.z(parent.normCurve($cur_time+parent.start)) + parent.inherit_velocity*parent.input1.translate.z)\"}\
				"
			knob $curNode.rotate "\
				{\"\
				((1-parent.inherit_velocity)*\
				(\[exists input1\]?parent.input1.rotate.x(parent.normCurve($cur_time+parent.start)) : 0) +\
				parent.inherit_velocity*\
				(\[exists input1\]?parent.input1.rotate.x:0)) +\
				parent.spread_yz * (2*random(this.seed, $cur_time*100,1)-1)\"}\
				
				{\"\
				((1-parent.inherit_velocity)*\
				(\[exists input1\]?parent.input1.rotate.y(parent.normCurve($cur_time+parent.start)) : 0) +\
				parent.inherit_velocity*\
				(\[exists input1\]?parent.input1.rotate.y:0)) +\
				parent.spread_xz * (2*random(this.seed+5, $cur_time*100,2)-1)\"}\
				
				{\"\
				((1-parent.inherit_velocity)*\
				(\[exists input1\]?parent.input1.rotate.z(parent.normCurve($cur_time+parent.start)) : 0) +\
				parent.inherit_velocity*\
				(\[exists input1\]?parent.input1.rotate.z:0))\"}\
				"
			knob $curNode.name "Spread_$counter"
			knob $curNode.label "auto generated"
			#input $curNode 1 Emitter
			lappend NewNodes $curNode

			#FORCES #############################################################
			TransformGeo -New
			set curNode [stack 0]
			knob $curNode.selectable false
			knob $curNode.translate "\
				{\"(pow(frame-parent.start-$cur_time,2) * parent.wind.x)\"}\
				{\"(pow(frame-parent.start-$cur_time,2) * -parent.gravity/100) + (pow(frame-parent.start-$cur_time,2) * parent.wind.y)\"}\
				{\"(pow(frame-parent.start-$cur_time,2) * parent.wind.z)\"}\
				"
			if {[knob type] == "sprite"} {input $curNode 2 lookAt}
			knob $curNode.name "Forces_$counter"
			knob $curNode.label "auto generated"
			lappend NewNodes $curNode

			##END OF NODE GENERATION #############################################################
			input MasterScene $counter $curNode
			incr counter
			}
		
		eval [concat autoplace $NewNodes]
		}
}
