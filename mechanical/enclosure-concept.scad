// V0.1 SPACE STUDY ONLY. Units: mm. No fabrication-ready holes or tolerances.
// All dimensions are project assumptions, not verified component dimensions.
case_w = 220;
case_d = 180;
case_h = 70;
wall = 2;
pcb_w = 140;
pcb_d = 100;
pcb_t = 1.6;
pcb_z = 10;
sink_w = 80;
sink_d = 60;
sink_h = 35;
sink_base_z = 18; // placeholder, not the actual IC contact height
show_lid = false;

assert(case_w > pcb_w + 2*wall && case_d > pcb_d + 2*wall);
assert(case_h > sink_base_z + sink_h + wall);

color([0.7,0.72,0.75,0.3]) difference() {
    cube([case_w,case_d,case_h]);
    translate([wall,wall,wall])
        cube([case_w-2*wall,case_d-2*wall,case_h]);
}
color("green") translate([(case_w-pcb_w)/2,(case_d-pcb_d)/2,pcb_z])
    cube([pcb_w,pcb_d,pcb_t]);
color([0.2,0.2,0.2,0.7])
    translate([(case_w-sink_w)/2,(case_d-sink_d)/2,sink_base_z])
        cube([sink_w,sink_d,sink_h]);
if (show_lid) color([0.7,0.72,0.75,0.3])
    translate([0,0,case_h]) cube([case_w,case_d,wall]);
