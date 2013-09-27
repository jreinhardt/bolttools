module singlerowradialbearing(d1,d2,B,detailed){
	if(detailed){
		//TODO: do this
		cube();
	} else {
		translate([0,0,B/2]){
			difference(){
				cylinder(r=d2/2,h=B,center=true);
				cylinder(r=d1/2,h=B+0.01,center=true);
			}
		}
	}
}
