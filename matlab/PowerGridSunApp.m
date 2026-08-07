classdef PowerGridSunApp < handle
    properties
        UIFigure matlab.ui.Figure
        APIBase matlab.ui.control.EditField
        CampusLoad matlab.ui.control.Label
        PowerFactor matlab.ui.control.Label
        AlertCount matlab.ui.control.Label
        AssetTable matlab.ui.control.Table
        Log matlab.ui.control.TextArea
        Timer timer
    end
    methods
        function app = PowerGridSunApp()
            app.UIFigure = uifigure(Name="Power Grid Sun — EES Industrial Power Twin",Position=[80 80 1180 720]);
            gl=uigridlayout(app.UIFigure,[4 4]); gl.RowHeight={44,90,'1x',150}; gl.ColumnWidth={'1x','1x','1x','2x'};
            uilabel(gl,Text="Railway API",FontWeight="bold");
            app.APIBase=uieditfield(gl,'text',Value="http://localhost:8000",Layout=struct('Row',1,'Column',[2 3]));
            b=uibutton(gl,Text="Refresh",ButtonPushedFcn=@(~,~)app.refresh()); b.Layout.Row=1;b.Layout.Column=4;
            app.CampusLoad=uilabel(gl,Text="Campus Load\n-- kW",FontSize=20,FontWeight="bold"); app.CampusLoad.Layout.Row=2;app.CampusLoad.Layout.Column=1;
            app.PowerFactor=uilabel(gl,Text="Power Factor\n--",FontSize=20,FontWeight="bold"); app.PowerFactor.Layout.Row=2;app.PowerFactor.Layout.Column=2;
            app.AlertCount=uilabel(gl,Text="Open Alerts\n--",FontSize=20,FontWeight="bold"); app.AlertCount.Layout.Row=2;app.AlertCount.Layout.Column=3;
            run=uibutton(gl,Text="Run Simulation Tick",ButtonPushedFcn=@(~,~)app.tick()); run.Layout.Row=2;run.Layout.Column=4;
            app.AssetTable=uitable(gl,ColumnName={'Code','Asset','Facility','kW','A','PF','Temp C','Health','Fault'}); app.AssetTable.Layout.Row=3;app.AssetTable.Layout.Column=[1 4];
            app.Log=uitextarea(gl,Editable='off'); app.Log.Layout.Row=4;app.Log.Layout.Column=[1 4];
            app.refresh();
        end
        function refresh(app)
            try
                s=webread(app.APIBase.Value+"/api/v1/system/current");
                app.CampusLoad.Text=sprintf("Campus Load\n%.1f kW",s.campus.real_power_kw);
                app.PowerFactor.Text=sprintf("Power Factor\n%.3f",s.campus.power_factor);
                app.AlertCount.Text=sprintf("Open Alerts\n%d",s.campus.open_alerts);
                a=s.assets; data=cell(numel(a),9);
                for i=1:numel(a), data(i,:)={a(i).code,a(i).name,a(i).facility,a(i).real_power_kw,a(i).current_a,a(i).power_factor,a(i).temperature_c,a(i).health_pct,string(a(i).fault_code)}; end
                app.AssetTable.Data=data; app.log("Snapshot refreshed.");
            catch e, app.log("Refresh failed: "+e.message); end
        end
        function tick(app)
            try
                opts=weboptions(MediaType="application/json",HeaderFields=["X-API-Key","change-me"]);
                webwrite(app.APIBase.Value+"/api/v1/simulation/tick",struct("minutes",1,"fault_probability",0.01),opts);
                app.refresh(); app.log("Simulation tick stored in PostgreSQL.");
            catch e, app.log("Tick failed: "+e.message); end
        end
        function log(app,msg), app.Log.Value=[string(datetime("now"))+"  "+msg; string(app.Log.Value)]; end
    end
end
