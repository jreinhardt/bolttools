include <common/conf.scad>
include <common/common.scad>
include <base/baseparams.scad>
include <base/multitable.scad>
include <base/hex.scad>
include <tables/ISO4014_table.scad>
module ISO4014(key="", l=10){
	check_parameter_type("ISO4014","key",key,"Table Index");
	check_parameter_type("ISO4014","l",l,"Length (mm)");

	measures_0 = ISO4014_table_0(key);
	if(measures_0 == "Error"){
		echo("TableLookUpError in ISO4014, table 0");
	}
	if(BOLTS_MODE == "bom"){
		echo(str(" ","Hexagon"," ","head"," ","bolt"," ","ISO4014"," ","-"," ",key," ",l," "));
		cube();
	} else {
		hex2(convert_to_default_unit(measures_0[0],"mm"), convert_to_default_unit(measures_0[1],"mm"), convert_to_default_unit(measures_0[2],"mm"), convert_to_default_unit(measures_0[3],"mm"), convert_to_default_unit(measures_0[4],"mm"), convert_to_default_unit(measures_0[5],"mm"), l);
	}
}

