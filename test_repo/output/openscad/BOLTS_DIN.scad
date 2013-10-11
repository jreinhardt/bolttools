include <common/conf.scad>
include <common/common.scad>
include <base/baseparams.scad>
include <base/multitable.scad>
include <base/hex.scad>
include <tables/DIN931_table.scad>
include <tables/DIN933_table.scad>
include <tables/DIN625_1_table.scad>
module DIN931(key="", l=10){
	echo("Warning: The standard DIN931 is withdrawn.
Although withdrawn standards are often still in use,
it might be better to use its successor DINEN24014 instead");
	check_parameter_type("DIN931","key",key,"Table Index");
	check_parameter_type("DIN931","l",l,"Length (mm)");

	measures_0 = DIN931_table_0(key);
	if(measures_0 == "Error"){
		echo("TableLookUpError in DIN931, table 0");
	}
	if(BOLTS_MODE == "bom"){
		echo(str(" ","Hexagon"," ","head"," ","bolt"," ","DIN931"," ","-"," ",key," ",l," "));
		cube();
	} else {
		hex2(convert_to_default_unit(measures_0[0],"mm"), convert_to_default_unit(measures_0[1],"mm"), convert_to_default_unit(measures_0[2],"mm"), convert_to_default_unit(measures_0[3],"mm"), convert_to_default_unit(measures_0[4],"mm"), convert_to_default_unit(measures_0[5],"mm"), l);
	}
}

module DIN933(key="", l=10){
	echo("Warning: The standard DIN933 is withdrawn.
Although withdrawn standards are often still in use,
it might be better to use its successor None instead");
	check_parameter_type("DIN933","key",key,"Table Index");
	check_parameter_type("DIN933","l",l,"Length (mm)");

	measures_0 = DIN933_table_0(key);
	if(measures_0 == "Error"){
		echo("TableLookUpError in DIN933, table 0");
	}
	measures_1 = DIN933_table_1(key);
	if(measures_1 == "Error"){
		echo("TableLookUpError in DIN933, table 1");
	}
	if(BOLTS_MODE == "bom"){
		echo(str(" ","Hexagon"," ","head"," ","screw"," ","DIN933"," ","-"," ",key," ",l," "));
		cube();
	} else {
		hex1(convert_to_default_unit(measures_0[0],"mm"), convert_to_default_unit(measures_0[1],"mm"), convert_to_default_unit(measures_0[2],"mm"), convert_to_default_unit(measures_1[1],"mm"), l);
	}
}

module DIN625_1(key="608", detailed=False){
	check_parameter_type("DIN625-1","key",key,"Table Index");
	check_parameter_type("DIN625-1","detailed",detailed,"Bool");

	measures_0 = DIN625_1_table_0(key);
	if(measures_0 == "Error"){
		echo("TableLookUpError in DIN625-1, table 0");
	}
	if(BOLTS_MODE == "bom"){
		echo(str(" ","Ball"," ","bearing"," ","DIN625-1"," ",key," "));
		cube();
	} else {
		singlerowradialbearing(convert_to_default_unit(measures_0[0],"mm"), convert_to_default_unit(measures_0[1],"mm"), convert_to_default_unit(measures_0[2],"mm"));
	}
}

