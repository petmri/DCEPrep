%% INPUTS
%-----------
% Human CBF = 22-55 ml/min/100ml (Leenders et al Brain 1990)
% Human CBV = 2.7-8.6% (Leenders et al Brain 1990)
% Human CBV = 1.3%,2.6% WM,GM (Sourbron et al MRM 2009)
% Rat CBF in parietal cortex = 129�18 ml/100g/min  (Adam et al JCBFM 2003)
% Rat CBV in parietal cortex = 2.1�0.38 ml/100g  (Adam et al JCBFM 2003)
% Human/Rat Ve Brain = 5% - 9% (He MRM 2007, Bender MRM 2009)
% Human/Rat Ve Brain = 15% - 30% (Sykova Physiol Rev 2008)
% Ktrans health brain = 0.5-3*10^-3/min (Taheri 2011 and our data)
% Ktrans rat brain = 0 - 0.6*10^-3/min (Ewing 2003)
% Ktrans glioma = 10-50*10^-3/min (Choi 2013)
snr_adjust = 0;
double_fit = 1;
average_across_offset = true;
show_plots = true;
save_data = true;

% Full Run
% ktrans_list     = logspace(-1,1.7,20).*10^-3; % in /min or ml/min/ml
% vp_list         = [0.01 0.02 0.04 0.08];         % in volume fraction (ml/ml)
% ve_list         = [0.03 0.1 0.3];              % in volume fraction (ml/ml)
% fp_list         = [0.20 0.60];         % in ml/min/ml or /min
% % PS            = derived from Fp and Ktrans = (Fp*PS)/(Fp + PS)
% ta_list         = [5 15 30];                % in minutes
% snr_list        = [30 300];               % SNR of the pre SI
% noise_repeats   = 200;
% time_resolution_list = [0.5 1.0 15.4 90];         % in seconds (15.4 human)
% baseline_time   = 91;       % in seconds, time to collect baseline images

% GPU ETofts Run
ktrans_list     = [10 20 30 40 50 60 70 80 90].*10^-3; % in /min or ml/min/ml
vp_list         = [0.05];         % in volume fraction (ml/ml)
ve_list         = [0.4];              % in volume fraction (ml/ml)
fp_list         = [1];         % in ml/min/ml or /min
% PS            = derived from Fp and Ktrans = (Fp*PS)/(Fp + PS)
ta_list         = [5];                % in minutes
snr_list        = [5 50];               % SNR of the pre SI
noise_repeats   = 100;
time_resolution_list = [1];         % in seconds (15.4 human)
time_offset_list= [0];
baseline_time   = 15;       % in seconds, time to collect baseline images

% number_cpus     = 4;
fit_dce_model   ='ex_tofts';        % used to fit the tissue curve
                                    % tofts, ex_tofts, 2cxm, patlak, 
                                    % tissue_uptake, fxr, auc
gen_dce_model   ='2cxm';            % used to generate the tissue curve
                                    % ex_tofts, patlak, 2cxm, 2cxm_binding
aif_curve       = 'parker_multihance';         % 'tofts' 'usc' 'parker' 
                                    % 'parker_multihance' 'exponential'
max_gd_aif      = 2;                % in mmol, exponential model only
gd_decay_time   = 10;               % in minutes, exponential model only

aif_t1_pre      = 1200;     % in ms
tissue_t1_pre   = 1800;     % in ms
alpha           = 1000;     % arbitrary scalar for SI
tr              = 8.3;      % in ms
fa              = 15;       % in degrees
relaxivity      = 5.5;      % in /mM/sec
% baseline_images = ;       % number of collected baseline images
Ka              = 1.5;      % binding constant in /mM, for 2cxm_binding 

time_resolution_list = time_resolution_list./60;%convert to minutes
baseline_time = baseline_time./60;              %convert to minutes
time_offset_list = time_offset_list./-60;       %convert to minutes
% ROI_size = 100;
% snr_list = [snr_list; snr_list*sqrt(ROI_size)];
%-----------

%% Processing
% Sanity check
if max(ktrans_list)>=min(fp_list)
    error('Ktrans cannot be greater than Fp');
end
if max(time_resolution_list)>baseline_time
    error('Baseline shorter than time resolution, would result in zero baseline images');
end
        
disp('Starting Simulation')
disp(datestr(now))
disp(' ');
tic

% Inner variables can all be run with a single call to the fitting function
inner_variable_sizes = [length(ktrans_list) length(vp_list) length(ve_list) length(fp_list)];
length_inner_variables = length(ktrans_list)*length(vp_list)*length(ve_list)*length(fp_list);
% Outer variables involve changes to the AIF and therefore require multiple
% calls to the fitting function
outer_variable_sizes = [noise_repeats length(ta_list) length(time_resolution_list) length(time_offset_list) length(snr_list)];
length_outer_variables = noise_repeats*length(ta_list)*length(time_resolution_list)*length(time_offset_list)*length(snr_list);
toffset_location = numel(inner_variable_sizes)+4;
repeats_location = numel(inner_variable_sizes)+1;

% number_time_arrays = length(ta_list)*length(time_resolution_list);
% time_array_length = 0;
% time_array_list = cell(number_time_arrays,1);
% for i=1:number_time_arrays
%     [ta_index, tres_index] = ind2sub([length(ta_list) length(time_resolution_list)],i);
%     ta = ta_list(ta_index);
%     time_resolution = time_resolution_list(tres_index);
%     
%     time_array_list{i} = 0:time_resolution:ta;
%     time_array_list{i} = time_array_list{i}+time_offset;
%     time_array_list{i}(1) = 0;
%     if length(time_array_list{i})>time_array_length
%         time_array_length = length(time_array_list{i});
%     end
% end
% All time arrays need to be the same size, pad with zeros
% for i=1:length(ta_list)
%     time_array_list{i} = cat(2,zeros(1,time_array_length-length(time_array_list{i})),time_array_list{i});
% end

% Reserve Space for results
exponential_ktrans = zeros(length_inner_variables,length_outer_variables);
exponential_vp = zeros(length_inner_variables,length_outer_variables);
exponential_ve = zeros(length_inner_variables,length_outer_variables);
exponential_fp = zeros(length_inner_variables,length_outer_variables);

exponential_residual = zeros(length_inner_variables,length_outer_variables);
exponential_ktrans_95ci = zeros(length_inner_variables,length_outer_variables,2);
exponential_vp_95ci = zeros(length_inner_variables,length_outer_variables,2);
exponential_ve_95ci = zeros(length_inner_variables,length_outer_variables,2);
exponential_fp_95ci = zeros(length_inner_variables,length_outer_variables,2);

if double_fit
    d_exponential_ktrans = zeros(length_inner_variables,length_outer_variables);
    d_exponential_vp = zeros(length_inner_variables,length_outer_variables);
    d_exponential_ve = zeros(length_inner_variables,length_outer_variables);
    d_exponential_fp = zeros(length_inner_variables,length_outer_variables);

    d_exponential_residual = zeros(length_inner_variables,length_outer_variables);
    d_exponential_ktrans_95ci = zeros(length_inner_variables,length_outer_variables,2);
    d_exponential_vp_95ci = zeros(length_inner_variables,length_outer_variables,2);
    d_exponential_ve_95ci = zeros(length_inner_variables,length_outer_variables,2);
    d_exponential_fp_95ci = zeros(length_inner_variables,length_outer_variables,2);
end


% Launch pool if not already running, then disable warnings
poolobj = gcp;
pctRunOnAll warning 'off'


% pp = ProgressBar(length_inner_variables*length_outer_variables);
barWidth= int32( 100/3 );
if length_outer_variables>10000
    progessbar_outer = 1;
else
    progessbar_outer = 0;
end

if progessbar_outer
    if length_outer_variables>1000000
        warning('timed progress bar could significantly slow simulation');
    end
    pp =  TimedProgressBar( length_outer_variables, barWidth, ...
        'Time Remaining: ', ', completed ', 'Concluded in ' );
else
    if length_inner_variables*length_outer_variables>1000000
        warning('timed progress bar could significantly slow simulation');
    end
    pp =  TimedProgressBar( length_inner_variables*length_outer_variables, barWidth, ...
        'Time Remaining: ', ', completed ', 'Concluded in ' );
end

% Outer loop is over variables that require changes to the AIF (noise, TA,
% time res, SNR)
for j=1:length_outer_variables
    if progessbar_outer
        pp.progress;
    end
    [repeats_index, ta_index, tres_index, toffset_index, snr_index] = ind2sub(outer_variable_sizes,j);
    ta = ta_list(ta_index);
    time_resolution = time_resolution_list(tres_index);
    time_offset = time_offset_list(toffset_index);
    snr_level = snr_list(snr_index);
    
    % For time resolution simulation
    if snr_adjust
        if time_resolution==0.25
            snr_level = 30;
        elseif time_resolution==1.0
            snr_level = 60;
        elseif time_resolution==4.0
            snr_level = 120;
        end
    end
    
    % The curve generation and down sampling is time consuming, do not
    % repeat if doing a noise repeat
    if repeats_index==1
        time_array = 0:time_resolution:ta;
        time_array = time_array+time_offset;
        time_array(1) = 0;

        baseline_images = floor(baseline_time/time_resolution_list(tres_index));
        % Reserve Space for tissue matrix
    %     if j==1
    %         noise_stdv = zeros(length(time_array),1);
    %         noise_stdv_tissue = zeros(length(time_array),length_inner_variables);
    %         noise_stdv_tissue_avg = zeros(length(time_array)/6,length_inner_variables);
    %     end
    %     
    %     tissue_si_matrix = zeros(length(time_array),length_inner_variables);
    %     tissue_si_noisy_matrix = zeros(length(time_array),length_inner_variables);
        tissue_gd_matrix = zeros(length(time_array),length_inner_variables);
        tissue_gd_matrix_noisy = zeros(length(time_array),length_inner_variables);

        % Calculate AIF concentration and SI
        if strcmp(aif_curve, 'tofts')
            % Tofts JMRI 1997 published AIF
            dose = 0.05; % in mmole/kg
            A = dose * 3.99;
            B = dose * 4.78;
            c = 0.144;
            d = 0.011;
            aif_function = @(t) (A*exp(-c*t)+B*exp(-d*t)).*logical(t);
        elseif strcmp(aif_curve, 'usc')
            % USC Fitted AIF
            A = 1.0372;
            B = 0.8375;
            c = 0.0155;
            d = 0.5115;
            aif_function = @(t) (A*exp(-c*t)+B*exp(-d*t)).*logical(t);
        elseif strcmp(aif_curve, 'parker')    
            % Parker et al. MRM 2006
            A_aif_1     = 0.809;
            sigma_aif_1 = 0.0563;
            T_aif_1     = 0.17046;
            A_aif_2     = 0.330;
            sigma_aif_2 = 0.132;
            T_aif_2     = 0.365;
            alpha_aif   = 1.050;
            beta_aif    = 0.1685;
            s_aif       = 38.078;
            tau_aif     = 0.483;

            aif_function = @(t) (A_aif_1./(sigma_aif_1.*sqrt(2.*pi())).*exp(-(t-T_aif_1).^2./(2.*sigma_aif_1.^2)) + ...
                A_aif_2./(sigma_aif_2.*sqrt(2.*pi()))*exp(-(t-T_aif_2).^2./(2.*sigma_aif_2.^2)) + ...
                alpha_aif.*exp(-beta_aif.*t)./(1+exp(-s_aif.*(t-tau_aif))) ).*logical(t);
        elseif strcmp(aif_curve, 'parker_multihance')
            % Multihance estimate using Parker et al. MRM 2006 as baseline
            A_aif_1     = 0.409; %
            sigma_aif_1 = 0.0563;
            T_aif_1     = 0.17046;
            A_aif_2     = 0.160; %
            sigma_aif_2 = 0.132;
            T_aif_2     = 0.365;
            alpha_aif   = 0.6646; %
            beta_aif    = 0.5819;
            alpha_aif_2   = 0.6695; %
            beta_aif_2    = 0.0175; %
            s_aif       = 38.078;
            tau_aif     = 0.483;

            aif_function = @(t) (A_aif_1./(sigma_aif_1.*sqrt(2.*pi())).*exp(-(t-T_aif_1).^2./(2.*sigma_aif_1.^2)) + ...
                A_aif_2./(sigma_aif_2.*sqrt(2.*pi()))*exp(-(t-T_aif_2).^2./(2.*sigma_aif_2.^2)) + ...
                alpha_aif.*exp(-beta_aif.*t)./(1+exp(-s_aif.*(t-tau_aif))) + ...
                alpha_aif_2.*exp(-beta_aif_2.*t)./(1+exp(-s_aif.*(t-tau_aif))) ).*logical(t);
        elseif strcmp(aif_curve, 'exponential')
            % Simple exponential with parameters specified above
            aif_function = @(t) (max_gd_aif*exp(-t/gd_decay_time)).*logical(t);
        else
            error([aif_curve ' is not a valid AIF curve']);
        end

    %     aif_gd = arrayfun(aif_function,time_array);
        aif_gd = down_sample(aif_function,time_array,0.1/60);
        aif_t1_post = 1./(1/aif_t1_pre+aif_gd.*(relaxivity*1/1000));
        aif_si_pre = sind(fa)*alpha*(1-exp(-tr/aif_t1_pre))/(1-cosd(fa)*exp(-tr/aif_t1_pre));
        aif_si_post = sind(fa).*alpha.*(1-exp(-tr./aif_t1_post))./(1-cosd(fa).*exp(-tr./aif_t1_post));
    end
    
    % Add noise to SI, noise is in the real and img channels when
    % aquired, the mag is then taken for the image, this gives the noise
    % (which is white Gaussian for the acquisition) a Rician distribution
    noise_real = normrnd(0,mean(aif_si_pre)/snr_level,size(aif_si_post));
    noise_img = normrnd(0,mean(aif_si_pre)/snr_level,size(aif_si_post));
    aif_si_post_noisy = sqrt( (aif_si_post+noise_real).^2 + noise_img.^2);
    noise_real = normrnd(0,mean(aif_si_pre)/(snr_level*sqrt(baseline_images)),size(aif_si_pre));
    noise_img = normrnd(0,mean(aif_si_pre)/(snr_level*sqrt(baseline_images)),size(aif_si_pre));
    aif_si_pre_noisy = sqrt( (aif_si_pre+noise_real).^2 + noise_img.^2);
    
    % Now get the noisy aif concentration
    sstar = (1-exp(-tr/aif_t1_pre))/(1-cosd(fa)*exp(-tr/aif_t1_pre));
    si_ratio_noisy = aif_si_post_noisy./aif_si_pre_noisy;
    aif_r1_post_noisy = -1./tr*log((sstar.*si_ratio_noisy-1)./(si_ratio_noisy.*sstar.*cosd(fa)-1));
    aif_gd_noisy = (aif_r1_post_noisy-1/aif_t1_pre)/(relaxivity/1000);
    %Remove any complex points (introduced if lots of noise)
    max_aif = max(real(aif_gd_noisy));
    aif_gd_noisy(aif_gd_noisy~=real(aif_gd_noisy)) = max_aif;

%     noise_stdv(:,1) = ((aif_si_post-aif_si_post_noisy).^2)'+noise_stdv(:,1);

    % Inner loop is for variables that just change the tissue curve
    % (ktrans, Vp, Ve), this loop generates tissue curves, and caches
    % them for future noise repeats
    for i=1:length_inner_variables
        if ~progessbar_outer
            pp.progress;
        end
        
        [k_index, vp_index, ve_index, Fp_index] = ind2sub(inner_variable_sizes,i);
        ktrans  = ktrans_list(k_index);
        vp      = vp_list(vp_index);
        ve      = ve_list(ve_index);
        Fp      = fp_list(Fp_index);
        PS      = ktrans*Fp/(Fp-ktrans);
        
        % The curve generation and down sampling is time consuming, only
        % caclulate on first noise repeat and cache values
        if repeats_index==1
            % Calculate Tissue SI
            if strcmp(gen_dce_model, 'ex_tofts')
                integral_function = @(u,t) aif_function(u).*exp(-ktrans*(t-u)/ve);
                tissue_function = @(t) ktrans*integral(@(u)integral_function(u,t),0,t)+vp*aif_function(t);
            elseif strcmp(gen_dce_model, 'patlak')
                tissue_function = @(t) ktrans*integral(@(u)aif_function(u),0,t)+vp*aif_function(t);
            elseif strcmp(gen_dce_model, '2cxm')
                E = PS/(PS+Fp);
                e = ve/(vp+ve);
                tau_plus  = (E-E*e+e)/(2*E)*(1+sqrt(1-(4*E*e*(1-E)*(1-e))/(E-E*e+e)^2));
                tau_minus = (E-E*e+e)/(2*E)*(1-sqrt(1-(4*E*e*(1-E)*(1-e))/(E-E*e+e)^2));
                k_plus  = Fp/((vp+ve)*tau_minus);
                k_minus = Fp/((vp+ve)*tau_plus);
                F_plus  =  1*Fp*(tau_plus-1)/(tau_plus-tau_minus);
                F_minus = -1*Fp*(tau_minus-1)/(tau_plus-tau_minus);
                integral_function = @(u,t) aif_function(u).*(F_plus*exp(-k_plus*(t-u)) + F_minus*exp(-k_minus*(t-u)));
                tissue_function = @(t) integral(@(u)integral_function(u,t),0,t);
            elseif strcmp(gen_dce_model, '2cxm_binding')
                Cinit = [0,0];              % initial value for Plasma and EEV

                % write down the expressions for the fluxes
                % C(1) = concentration plasma   C(2) = concentration EEV
                Pi = @(t,C) PS.*C(2) + Fp.*aif_function(t); % influx to Plasma
                Pe = @(t,C,ub) PS*ub.*C(1) + Fp.*C(1);      % efflux from Plasma
                Ei = @(t,C,ub) PS*ub.*C(1);                 % influx to EEV
                Ee = @(t,C) PS.*C(2);                       % efflux from EEV

                % solve the differential equation 
                ode_solution = ode45(@TwoCompModelBinding,[0 ta],Cinit,[],Pi,Pe,Ei,Ee,vp,ve,Ka);

                % Get tissue curve
                c_compartments = deval(ode_solution,time_array);
                c_tissue = vp.*c_compartments(1,:)+ve.*c_compartments(2,:);
            else
                error([gen_dce_model ' is not a valid generation model']);
            end

            if strcmp(gen_dce_model, '2cxm_binding')
                tissue_gd_matrix(:,i) = c_tissue;
            else
    %             tissue_gd_matrix(:,i) = arrayfun(tissue_function,time_array);
                tissue_gd_matrix(:,i) = down_sample(tissue_function,time_array,1/60);
            end      
        end
        
        tissue_t1_post = 1./(1/tissue_t1_pre+tissue_gd_matrix(:,i).*(relaxivity*1/1000));
        tissue_si_pre = sind(fa)*alpha*(1-exp(-tr/tissue_t1_pre))/(1-cosd(fa)*exp(-tr/tissue_t1_pre));
        tissue_si_post = sind(fa).*alpha.*(1-exp(-tr./tissue_t1_post))./(1-cosd(fa).*exp(-tr./tissue_t1_post));
        
        % Add noise to SI, noise is in the real and img channels when
        % aquired, the mag is then taken for the image, this gives the noise
        % (which is white Gaussian for the acquisition) a Rician distribution
        noise_real_post = normrnd(0,mean(tissue_si_pre)/snr_level,size(tissue_si_post));
        noise_img_post = normrnd(0,mean(tissue_si_pre)/snr_level,size(tissue_si_post));
        tissue_si_post_noisy = sqrt( (tissue_si_post+noise_real_post).^2 + noise_img_post.^2);
        noise_real = normrnd(0,mean(tissue_si_pre)/(snr_level*sqrt(baseline_images)),size(tissue_si_pre));
        noise_img = normrnd(0,mean(tissue_si_pre)/(snr_level*sqrt(baseline_images)),size(tissue_si_pre));
        tissue_si_pre_noisy = sqrt( (tissue_si_pre+noise_real).^2 + noise_img.^2);

        % Now get the noisy tissue concentration
        sstar = (1-exp(-tr/tissue_t1_pre))/(1-cosd(fa)*exp(-tr/tissue_t1_pre));
        si_ratio_noisy = tissue_si_post_noisy./tissue_si_pre_noisy;
        tissue_r1_post_noisy = -1./tr*log((sstar.*si_ratio_noisy-1)./(si_ratio_noisy.*sstar.*cosd(fa)-1));
        tissue_gd_matrix_noisy(:,i) = (tissue_r1_post_noisy-1/tissue_t1_pre)/(relaxivity/1000);
%         figure(1)
%         plot(tissue_gd_matrix(:,i));
%         tissue_si_matrix(:,i) = tissue_si_post;
%         tissue_si_noisy_matrix(:,i) = tissue_si_post_noisy;
%         noise_stdv_tissue(:,i) = ((tissue_si_post-tissue_si_post_noisy).^2)+noise_stdv_tissue(:,i);
    end

    
    % A single call returns all the inner variable fits
    roi_data{1}.Cp = aif_gd_noisy;
    roi_data{1}.timer = time_array';
    roi_data{1}.Ct = tissue_gd_matrix_noisy;

%     roi_data{1}.Cp = decimate(aif_gd_noisy,4);
%     roi_data{1}.timer = decimate(time_array',4);
%     Ct_downsampled = zeros(size(roi_data{1}.Cp,2),size(tissue_gd_matrix_noisy,2));
%     for ii=1:size(tissue_gd_matrix_noisy,2)
%         Ct_downsampled(:,ii) = decimate(tissue_gd_matrix_noisy(:,ii),4);
%     end
%     roi_data{1}.Ct = Ct_downsampled;

%     n = 6;
%     si_avg = reshape(mean(reshape(tissue_si_matrix,[n prod(size(tissue_si_matrix))/n])), [size(tissue_si_matrix,1)/n size(tissue_si_matrix,2)]);
%     si_noise_avg = reshape(mean(reshape(tissue_si_noisy_matrix,[n prod(size(tissue_si_noisy_matrix))/n])), [size(tissue_si_noisy_matrix,1)/n size(tissue_si_noisy_matrix,2)]);
%     noise_stdv_tissue_avg = ((si_avg-si_noise_avg).^2)+noise_stdv_tissue_avg;
%     
%     roi_data{1}.Cp = reshape(mean(reshape(aif_gd_noisy',[n prod(size(aif_gd_noisy'))/n])), [size(aif_gd_noisy',1)/n size(aif_gd_noisy',2)])';
%     roi_data{1}.timer = reshape(mean(reshape(time_array',[n prod(size(time_array'))/n])), [size(time_array',1)/n size(time_array',2)]);
%     roi_data{1}.Ct = reshape(mean(reshape(tissue_gd_matrix_noisy,[n prod(size(tissue_gd_matrix_noisy))/n])), [size(tissue_gd_matrix_noisy,1)/n size(tissue_gd_matrix_noisy,2)]);
    [roi_results, roi_residuals] = FXLfit_generic(roi_data, length_inner_variables, fit_dce_model, 0);
    
    % Save results
    if strcmp(fit_dce_model, 'tofts')
        exponential_ktrans(:,j) = roi_results(:,1);
        exponential_ve(:,j) = roi_results(:,2);
        exponential_residual(:,j) = roi_results(:,3);
        exponential_ktrans_95ci(:,j,:) = [roi_results(:,4) roi_results(:,5)];
        exponential_ve_95ci(:,j,:) = [roi_results(:,6) roi_results(:,7)];
        paramname = {'Ktrans'; 've'; 'residual'; 'ktrans_ci_low'; 'ktrans_ci_high'; 've_ci_low';'ve_ci_high'};
    elseif strcmp(fit_dce_model, '2cxm')
        exponential_ktrans(:,j) = roi_results(:,1);
        exponential_ve(:,j) = roi_results(:,2);
        exponential_vp(:,j) = roi_results(:,3);
        exponential_fp(:,j) = roi_results(:,4);
        exponential_residual(:,j) = roi_results(:,5);
        exponential_ktrans_95ci(:,j,:) = [roi_results(:,6) roi_results(:,7)];
        exponential_ve_95ci(:,j,:) = [roi_results(:,8) roi_results(:,9)];
        exponential_vp_95ci(:,j,:) = [roi_results(:,10) roi_results(:,11)];
        exponential_fp_95ci(:,j,:) = [roi_results(:,12) roi_results(:,13)];
        paramname = {'Ktrans'; 've'; 'vp';'fp'; 'residual'; 'ktrans_ci_low'; 'ktrans_ci_high'; 've_ci_low';'ve_ci_high'; 'vp_ci_low'; 'vp_ci_high'; 'fp_ci_low'; 'fp_ci_high'};
    elseif strcmp(fit_dce_model, 'ex_tofts') || strcmp(fit_dce_model, 'nested')
        exponential_ktrans(:,j) = roi_results(:,1);
        exponential_ve(:,j) = roi_results(:,2);
        exponential_vp(:,j) = roi_results(:,3);
        exponential_residual(:,j) = roi_results(:,4);
        exponential_ktrans_95ci(:,j,:) = [roi_results(:,5) roi_results(:,6)];
        exponential_ve_95ci(:,j,:) = [roi_results(:,7) roi_results(:,8)];
        exponential_vp_95ci(:,j,:) = [roi_results(:,9) roi_results(:,10)];
        paramname = {'Ktrans'; 've'; 'vp'; 'residual'; 'ktrans_ci_low'; 'ktrans_ci_high'; 've_ci_low';'ve_ci_high'; 'vp_ci_low'; 'vp_ci_high'};
    elseif strcmp(fit_dce_model, 'tissue_uptake')
        exponential_ktrans(:,j) = roi_results(:,1);
        exponential_ve(:,j) = roi_results(:,2); %actually fp
        exponential_vp(:,j) = roi_results(:,3);
        exponential_residual(:,j) = roi_results(:,4);
        exponential_ktrans_95ci(:,j,:) = [roi_results(:,5) roi_results(:,6)];
        exponential_ve_95ci(:,j,:) = [roi_results(:,7) roi_results(:,8)];
        exponential_vp_95ci(:,j,:) = [roi_results(:,9) roi_results(:,10)];
        paramname = {'Ktrans'; 'fp'; 'vp'; 'residual'; 'ktrans_ci_low'; 'ktrans_ci_high'; 'fp_ci_low';'fp_ci_high'; 'vp_ci_low'; 'vp_ci_high'};
    elseif strcmp(fit_dce_model, 'patlak') || strcmp(fit_dce_model, 'patlak_linear')
        exponential_ktrans(:,j) = roi_results(:,1);
        exponential_vp(:,j) = roi_results(:,2);
        exponential_residual(:,j) = roi_results(:,3);
        exponential_ktrans_95ci(:,j,:) = [roi_results(:,4) roi_results(:,5)];
        exponential_vp_95ci(:,j,:) = [roi_results(:,6) roi_results(:,7)];
        paramname = {'Ktrans'; 'vp'; 'residual'; 'ktrans_ci_low'; 'ktrans_ci_high'; 'vp_ci_low'; 'vp_ci_high'};
    elseif strcmp(fit_dce_model, 'fxr')
        exponential_ktrans(:,j) = roi_results(:,1);
        exponential_ve(:,j) = roi_results(:,2);
        exponential_vp(:,j) = roi_results(:,3);
        exponential_residual(:,j) = roi_results(:,4);
        exponential_ktrans_95ci(:,j,:) = [roi_results(:,5) roi_results(:,6)];
        exponential_ve_95ci(:,j,:) = [roi_results(:,7) roi_results(:,8)];
        exponential_vp_95ci(:,j,:) = [roi_results(:,9) roi_results(:,10)];
        paramname = {'Ktrans'; 've'; 'tau'; 'residual'; 'ktrans_ci_low'; 'ktrans_ci_high'; 've_ci_low';'ve_ci_high'; 'tau_ci_low'; 'tau_ci_high'};
    elseif strcmp(fit_dce_model, 'auc')
        if quant
            paramname = {'AUCc'; 'AUCs'; 'NAUCc'; 'NAUCs'};
        else
            paramname = {'AUCs'; 'NAUCs'};
        end
    else
        % Error
        error('Model not supported');
    end
    
    if double_fit
        [roi_results, roi_residuals] = FXLfit_generic(roi_data, length_inner_variables, fit_dce_model, 0, 1);
     
        if strcmp(fit_dce_model, 'tofts')
            d_exponential_ktrans(:,j) = roi_results(:,1);
            d_exponential_ve(:,j) = roi_results(:,2);
            d_exponential_residual(:,j) = roi_results(:,3);
            d_exponential_ktrans_95ci(:,j,:) = [roi_results(:,4) roi_results(:,5)];
            d_exponential_ve_95ci(:,j,:) = [roi_results(:,6) roi_results(:,7)];
            d_paramname = {'Ktrans'; 've'; 'residual'; 'ktrans_ci_low'; 'ktrans_ci_high'; 've_ci_low';'ve_ci_high'};
        elseif strcmp(fit_dce_model, '2cxm')
            d_exponential_ktrans(:,j) = roi_results(:,1);
            d_exponential_ve(:,j) = roi_results(:,2);
            d_exponential_vp(:,j) = roi_results(:,3);
            d_exponential_fp(:,j) = roi_results(:,4);
            d_exponential_residual(:,j) = roi_results(:,5);
            d_exponential_ktrans_95ci(:,j,:) = [roi_results(:,6) roi_results(:,7)];
            d_exponential_ve_95ci(:,j,:) = [roi_results(:,8) roi_results(:,9)];
            d_exponential_vp_95ci(:,j,:) = [roi_results(:,10) roi_results(:,11)];
            d_exponential_fp_95ci(:,j,:) = [roi_results(:,12) roi_results(:,13)];
            d_paramname = {'Ktrans'; 've'; 'vp';'fp'; 'residual'; 'ktrans_ci_low'; 'ktrans_ci_high'; 've_ci_low';'ve_ci_high'; 'vp_ci_low'; 'vp_ci_high'; 'fp_ci_low'; 'fp_ci_high'};
        elseif strcmp(fit_dce_model, 'ex_tofts') || strcmp(fit_dce_model, 'nested')
            d_exponential_ktrans(:,j) = roi_results(:,1);
            d_exponential_ve(:,j) = roi_results(:,2);
            d_exponential_vp(:,j) = roi_results(:,3);
            d_exponential_residual(:,j) = roi_results(:,4);
            d_exponential_ktrans_95ci(:,j,:) = [roi_results(:,5) roi_results(:,6)];
            d_exponential_ve_95ci(:,j,:) = [roi_results(:,7) roi_results(:,8)];
            d_exponential_vp_95ci(:,j,:) = [roi_results(:,9) roi_results(:,10)];
            d_paramname = {'Ktrans'; 've'; 'vp'; 'residual'; 'ktrans_ci_low'; 'ktrans_ci_high'; 've_ci_low';'ve_ci_high'; 'vp_ci_low'; 'vp_ci_high'};
        elseif strcmp(fit_dce_model, 'tissue_uptake')
            d_exponential_ktrans(:,j) = roi_results(:,1);
            d_exponential_ve(:,j) = roi_results(:,2); %actually fp
            d_exponential_vp(:,j) = roi_results(:,3);
            d_exponential_residual(:,j) = roi_results(:,4);
            d_exponential_ktrans_95ci(:,j,:) = [roi_results(:,5) roi_results(:,6)];
            d_exponential_ve_95ci(:,j,:) = [roi_results(:,7) roi_results(:,8)];
            d_exponential_vp_95ci(:,j,:) = [roi_results(:,9) roi_results(:,10)];
            d_paramname = {'Ktrans'; 'fp'; 'vp'; 'residual'; 'ktrans_ci_low'; 'ktrans_ci_high'; 'fp_ci_low';'fp_ci_high'; 'vp_ci_low'; 'vp_ci_high'};
        elseif strcmp(fit_dce_model, 'patlak') || strcmp(fit_dce_model, 'patlak_linear')
            d_exponential_ktrans(:,j) = roi_results(:,1);
            d_exponential_vp(:,j) = roi_results(:,2);
            d_exponential_residual(:,j) = roi_results(:,3);
            d_exponential_ktrans_95ci(:,j,:) = [roi_results(:,4) roi_results(:,5)];
            d_exponential_vp_95ci(:,j,:) = [roi_results(:,6) roi_results(:,7)];
            d_paramname = {'Ktrans'; 'vp'; 'residual'; 'ktrans_ci_low'; 'ktrans_ci_high'; 'vp_ci_low'; 'vp_ci_high'};
        end
    end


end
pp.stop;

%% Post Processing
% Verify Noise
% noise_stdv_sqrt = sqrt(noise_stdv/(length_outer_variables));
% noise_stdv_sqrt_tissue = sqrt(noise_stdv_tissue/(length_outer_variables));
% noise_stdv_sqrt_tissue_avg = sqrt(noise_stdv_tissue_avg/(length_outer_variables));
% actual_SNR_aif = aif_si_post./noise_stdv_sqrt';
% actual_SNR_tissue = tissue_si_matrix./noise_stdv_sqrt_tissue;
% actual_SNR_tissue_avg = si_avg./noise_stdv_sqrt_tissue_avg;


% actual_SNR = tissue_si_matrix./noise_stdv_sqrt;

% Check if data falls in 95% CI
% exponential_ktrans_95 = zeros(length_inner_variables,1);
% exponential_vp_95 = zeros(length_inner_variables,1);
% exponential_ve_95 = zeros(length_inner_variables,1);
% 
% for i=1:length_inner_variables
% 	for j=1:length_outer_variables	
% 		if exponential_ktrans(i,j)>min(exponential_ktrans_95ci(i,j,:)) && ...
% 				exponential_ktrans(i,j)<max(exponential_ktrans_95ci(i,j,:))
% 			exponential_ktrans_95(i) = exponential_ktrans_95(i)+1;
% 		end
% 		if exponential_vp(i,j)>min(exponential_vp_95ci(i,j,:)) && ...
% 				exponential_vp(i,j)<max(exponential_vp_95ci(i,j,:))
% 			exponential_vp_95(i) = exponential_vp_95(i)+1;
% 		end
% 		if exponential_ve(i,j)>min(exponential_ve_95ci(i,j,:)) && ...
% 				exponential_ve(i,j)<max(exponential_ve_95ci(i,j,:))
% 			exponential_ve_95(i) = exponential_ve_95(i)+1;
% 		end
% 	end
% end
% 
% exponential_ktrans_95 = exponential_ktrans_95./(length_outer_variables);
% exponential_vp_95 = exponential_vp_95./(length_outer_variables);
% exponential_ve_95 = exponential_ve_95./(length_outer_variables);

% Reshape
exponential_ktrans_shape = reshape(exponential_ktrans, [inner_variable_sizes outer_variable_sizes]);
exponential_vp_shape = reshape(exponential_vp, [inner_variable_sizes outer_variable_sizes]);
exponential_ve_shape = reshape(exponential_ve, [inner_variable_sizes outer_variable_sizes]);
exponential_fp_shape = reshape(exponential_fp, [inner_variable_sizes outer_variable_sizes]);

% Get the standard deviation error from the repeats
% exponential_ktrans_error_std = permute(exponential_ktrans_shape,[1 2 3 4 6 7 5 8]);
% exponential_ktrans_error_std = reshape(exponential_ktrans_error_std,[12 1 1 1 4 1 8*125]);
% exponential_ktrans_error_std = nanstd(exponential_ktrans_error_std,0,7);
exponential_ktrans_error_std = nanstd(exponential_ktrans_shape,0,repeats_location);
exponential_vp_error_std = nanstd(exponential_vp_shape,0,repeats_location);
exponential_ve_error_std = nanstd(exponential_ve_shape,0,repeats_location);
exponential_fp_error_std = nanstd(exponential_fp_shape,0,repeats_location);

% Average the repeats for bias error
exponential_ktrans_average = nanmean(exponential_ktrans_shape,repeats_location);
exponential_vp_average = nanmean(exponential_vp_shape,repeats_location);
exponential_ve_average = nanmean(exponential_ve_shape,repeats_location);
exponential_fp_average = nanmean(exponential_fp_shape,repeats_location);

exponential_ktrans_median = nanmedian(exponential_ktrans_shape,repeats_location);
exponential_vp_median = nanmedian(exponential_vp_shape,repeats_location);
exponential_ve_median = nanmedian(exponential_ve_shape,repeats_location);
exponential_fp_median = nanmedian(exponential_fp_shape,repeats_location);

% Remove signleton repeats dimension
sz = size(exponential_ktrans_median);
if size(sz)>repeats_location
    sz(repeats_location) = [];
end
exponential_ktrans_error_std = reshape(exponential_ktrans_error_std,sz);
exponential_vp_error_std = reshape(exponential_vp_error_std,sz);
exponential_ve_error_std = reshape(exponential_ve_error_std,sz);
exponential_fp_error_std = reshape(exponential_fp_error_std,sz);

exponential_ktrans_average = reshape(exponential_ktrans_average,sz);
exponential_vp_average = reshape(exponential_vp_average,sz);
exponential_ve_average = reshape(exponential_ve_average,sz);
exponential_fp_average = reshape(exponential_fp_average,sz);

exponential_ktrans_median = reshape(exponential_ktrans_median,sz);
exponential_vp_median = reshape(exponential_vp_median,sz);
exponential_ve_median = reshape(exponential_ve_median,sz);
exponential_fp_median = reshape(exponential_fp_median,sz);
% Reduce by one since the repeats dimension was removed
toffset_location = toffset_location-1;

% Subtract out the true values to get the bias error
exponential_ktrans_error = bsxfun(@minus,exponential_ktrans_average,ktrans_list');
% These don't work as the vp_list does not line up with the vp dimension
% exponential_vp_error = bsxfun(@minus,exponential_vp_average,vp_list');
% exponential_ve_error = bsxfun(@minus,exponential_ve_average,ve_list');
% exponential_fp_error = bsxfun(@minus,exponential_fp_average,fp_list');

exponential_ktrans_error_percent = bsxfun(@rdivide,exponential_ktrans_error,ktrans_list');
% These don't work as the vp_list does not line up with the vp dimension
% exponential_vp_error_percent = bsxfun(@rdivide,exponential_vp_error,vp_list');
% exponential_ve_error_percent = bsxfun(@rdivide,exponential_ve_error,ve_list');
% exponential_fp_error_percent = bsxfun(@rdivide,exponential_fp_error,fp_list');

if average_across_offset
    exponential_ktrans_error_std = nanmean(exponential_ktrans_error_std, toffset_location);
    exponential_vp_error_std = nanmean(exponential_vp_error_std, toffset_location);
    exponential_ve_error_std = nanmean(exponential_ve_error_std, toffset_location);
    exponential_fp_error_std = nanmean(exponential_fp_error_std, toffset_location);

    exponential_ktrans_average = nanmean(exponential_ktrans_average, toffset_location);
    exponential_vp_average = nanmean(exponential_vp_average, toffset_location);
    exponential_ve_average = nanmean(exponential_ve_average, toffset_location);
    exponential_fp_average = nanmean(exponential_fp_average, toffset_location);

    exponential_ktrans_median = nanmean(exponential_ktrans_median, toffset_location);
    exponential_vp_median = nanmean(exponential_vp_median, toffset_location);
    exponential_ve_median = nanmean(exponential_ve_median, toffset_location);
    exponential_fp_median = nanmean(exponential_fp_median, toffset_location);
    
    exponential_ktrans_error = nanmean(exponential_ktrans_error, toffset_location);
    exponential_ktrans_error_percent = nanmean(exponential_ktrans_error_percent, toffset_location);
end

if double_fit
    double_fit_gpu_run
end
% foo_std = exponential_ktrans_error_std.*1000;
% foo_mean = exponential_ktrans_average.*1000;
% exponential_ktrans_average = nanmean(exponential_ktrans_shape,number_variables);
% foo = squeeze(exponential_ktrans_average).*1000
% exponential_ktrans_error_std = nanstd(exponential_ktrans_shape,0,number_variables);
% foo = squeeze(exponential_ktrans_error_std).*1000

if(save_data)
    disp(' ');
    sim_save_name = ['simulation_' datestr(now,'yy-mm-dd-HH-MM-SS')];
    save(sim_save_name);
    disp(['Results saved to: ' sim_save_name]);
end
disp(' ');
disp('Finished');
disp(datestr(now))
toc

%% Make Plots
number_colors = 2*max([length(vp_list) length(ve_list) length(fp_list) length(ta_list) length(time_resolution_list) length(snr_list)]);
if number_colors<=4
    number_colors = 6;
end
set(0,'DefaultAxesColorOrder',hot(number_colors));    
ve_plot = 1;
ta_plot = 1;
snr_plot = 1;
vp_plot = 1;
fp_plot = 1;
ktrans_plot = 1;
tres_plot = 1;

if show_plots
    % Variable Order:
    % (Ktrans, Vp, Ve, Fp, TA, Time Res, SNR, noise repeats)
    % *********
  
    figure(1);
    p = plot(ktrans_list.*1000,squeeze(exponential_ktrans_error_percent(:,vp_plot,ve_plot,fp_plot,ta_plot,tres_plot,:)).*100);
    title([fit_dce_model ' GPU Accuracy Error'],'Interpreter','none');
    xlabel('Ktrans (10^{-3} * min^{-1})');
    ylabel('Accuracy Error (%)')
    legend(cellfun(@num2str,num2cell(snr_list),'UniformOutput', 0));
    %ylim([0 50])
%     savefig('fig1-AccuracyPercent');
%     saveas(gcf,'fig1-AccuracyPercent', 'png')
%  

    figure(2);
    p = plot(ktrans_list.*1000,squeeze(d_exponential_ktrans_error_percent(:,vp_plot,ve_plot,fp_plot,ta_plot,tres_plot,:)).*100);
    title([fit_dce_model ' CPU Accuracy Error'],'Interpreter','none');
    xlabel('Ktrans (10^{-3} * min^{-1})');
    ylabel('Accuracy Error (%)')
    legend(cellfun(@num2str,num2cell(snr_list),'UniformOutput', 0));
    %ylim([0 50])
%     savefig('fig1-AccuracyPercent');
%     saveas(gcf,'fig1-AccuracyPercent', 'png')
%  

    figure(3);
    p = scatter(exponential_ktrans(:),d_exponential_ktrans(:));
    title([fit_dce_model ' GPU vs. CPU fit Ktrans'],'Interpreter','none');
    xlabel('GPU Ktrans (10^{-3} * min^{-1})');
    ylabel('CPU Ktrans (10^{-3} * min^{-1})');
    %set(gca,'xscale','log');
    %set(gca,'yscale','log')
    ylim([0 0.2])
    xlim([0 0.2])
    
    figure(5);
    p = scatter(exponential_ve(:),d_exponential_ve(:));
    title([fit_dce_model ' GPU vs. CPU fit Ve'],'Interpreter','none');
    xlabel('GPU Ve');
    ylabel('CPU Ve');
    ylim([0 1])
    xlim([0 1])
    
    figure(6);
    p = scatter(exponential_vp(:),d_exponential_vp(:));
    title([fit_dce_model ' GPU vs. CPU fit Vp'],'Interpreter','none');
    xlabel('GPU Vp');
    ylabel('CPU Vp');
    ylim([0 0.1])
    xlim([0 0.1])
    

    figure(4);
    hold on
    p = errorbar(ktrans_list.*1000,squeeze(exponential_ktrans_median(:,vp_plot,ve_plot,fp_plot,ta_plot,tres_plot,1).*1000),squeeze(exponential_ktrans_error_std(:,vp_plot,ve_plot,fp_plot,ta_plot,tres_plot,1).*1000));
    p = errorbar(ktrans_list.*1000,squeeze(exponential_ktrans_median(:,vp_plot,ve_plot,fp_plot,ta_plot,tres_plot,2).*1000),squeeze(exponential_ktrans_error_std(:,vp_plot,ve_plot,fp_plot,ta_plot,tres_plot,2).*1000));
    hold off
    title([fit_dce_model ' fit vs. ' gen_dce_model ' Ktrans, Various SNR'],'Interpreter','none');
    xlabel('Ktrans (10^{-3} * min^{-1})');
    ylabel('Average Fit Ktrans (10^{-3} * min^{-1})')
    ylim([0 130])
    xlim([0 130])
    legend(cellfun(@num2str,num2cell(snr_list),'UniformOutput', 0), 'Location', 'NorthWest');
    diagonal_line = refline(1,0);
    set(diagonal_line,'Color',[0.5 0.5 0.5],'LineStyle',':');
    

%     figure(5)
%     plot(time_array,aif_gd_noisy,'k');

    
end


