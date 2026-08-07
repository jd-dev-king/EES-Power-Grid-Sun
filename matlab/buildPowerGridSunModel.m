function buildPowerGridSunModel()
% Programmatically creates the initial Simulink campus power-flow model.
model = "PowerGridSun";
if bdIsLoaded(model), close_system(model,0); end
new_system(model); open_system(model);
blocks = [
    "Utility Grid", 80,80,180,130;
    "Main Transformer", 260,80,390,130;
    "Main Switchgear", 470,80,590,130;
    "Pharma Plant", 700,20,820,70;
    "Logistics Facility", 700,95,840,145;
    "Utilities Plant", 700,170,820,220;
    "Executive Suites", 700,245,830,295];
for i=1:size(blocks,1)
    name=blocks(i,1); pos=str2double(blocks(i,2:5));
    add_block("simulink/Sources/Constant",model+"/"+name,Position=pos,Value="1");
end
add_line(model,"Utility Grid/1","Main Transformer/1");
add_line(model,"Main Transformer/1","Main Switchgear/1");
for target=["Pharma Plant","Logistics Facility","Utilities Plant","Executive Suites"]
    add_line(model,"Main Switchgear/1",target+"/1",Autorouting="on");
end
set_param(model,StopTime="3600");
save_system(model,fullfile(fileparts(mfilename("fullpath")),model+".slx"));
disp("Created PowerGridSun.slx");
end
