toffset_location = toffset_location+1;
% Reshape
d_exponential_ktrans_shape = reshape(d_exponential_ktrans, [inner_variable_sizes outer_variable_sizes]);
d_exponential_vp_shape = reshape(d_exponential_vp, [inner_variable_sizes outer_variable_sizes]);
d_exponential_ve_shape = reshape(d_exponential_ve, [inner_variable_sizes outer_variable_sizes]);
d_exponential_fp_shape = reshape(d_exponential_fp, [inner_variable_sizes outer_variable_sizes]);
d_exponential_residual_shape = reshape(d_exponential_residual, [inner_variable_sizes outer_variable_sizes]);
exponential_residual_shape = reshape(exponential_residual, [inner_variable_sizes outer_variable_sizes]);
exponential_ktrans_shape = reshape(exponential_ktrans, [inner_variable_sizes outer_variable_sizes]);

% % Throw out bad fits
% voxels_before = numel(d_exponential_ktrans_shape);
% residual_a_limit = 0.0113;
% d_exponential_ktrans_shape(d_exponential_residual_shape>residual_a_limit) = NaN;
% d_exponential_ve_shape(d_exponential_residual_shape>residual_a_limit) = NaN;
% d_exponential_vp_shape(d_exponential_residual_shape>residual_a_limit) = NaN;
% d_exponential_fp_shape(d_exponential_residual_shape>residual_a_limit) = NaN;
% exponential_ktrans_shape(d_exponential_residual_shape>residual_a_limit) = NaN;
% exponential_residual_shape(d_exponential_residual_shape>residual_a_limit) = NaN;
% d_exponential_residual_shape(d_exponential_residual_shape>residual_a_limit) = NaN;
% voxels_after_a = numel(d_exponential_ktrans_shape(~isnan(d_exponential_ktrans_shape)));
% 
% % residual_b_limit = 0.026;
% residual_b_limit = 0.0119;
% d_exponential_ktrans_shape(exponential_residual_shape>residual_b_limit) = NaN;
% d_exponential_ve_shape(exponential_residual_shape>residual_b_limit) = NaN;
% d_exponential_vp_shape(exponential_residual_shape>residual_b_limit) = NaN;
% d_exponential_fp_shape(exponential_residual_shape>residual_b_limit) = NaN;
% exponential_ktrans_shape(exponential_residual_shape>residual_b_limit) = NaN;
% d_exponential_residual_shape(exponential_residual_shape>residual_b_limit) = NaN;
% exponential_residual_shape(exponential_residual_shape>residual_b_limit) = NaN;
% voxels_after_b = numel(d_exponential_ktrans_shape(~isnan(d_exponential_ktrans_shape)));
% 
% percent_left_a_res_filter = voxels_after_a/voxels_before*100
% percent_left_b_res_filter = voxels_after_b/voxels_before*100



% Get the standard deviation error from the repeats
exponential_ktrans_error_std = nanstd(exponential_ktrans_shape,0,repeats_location);
d_exponential_ktrans_error_std = nanstd(d_exponential_ktrans_shape,0,repeats_location);
d_exponential_vp_error_std = nanstd(d_exponential_vp_shape,0,repeats_location);
d_exponential_ve_error_std = nanstd(d_exponential_ve_shape,0,repeats_location);
d_exponential_fp_error_std = nanstd(d_exponential_fp_shape,0,repeats_location);

% Average the repeats for bias error
exponential_ktrans_average = nanmean(exponential_ktrans_shape,repeats_location);
d_exponential_ktrans_average = nanmean(d_exponential_ktrans_shape,repeats_location);
d_exponential_vp_average = nanmean(d_exponential_vp_shape,repeats_location);
d_exponential_ve_average = nanmean(d_exponential_ve_shape,repeats_location);
d_exponential_fp_average = nanmean(d_exponential_fp_shape,repeats_location);

exponential_ktrans_median = nanmedian(exponential_ktrans_shape,repeats_location);
d_exponential_ktrans_median = nanmedian(d_exponential_ktrans_shape,repeats_location);
d_exponential_vp_median = nanmedian(d_exponential_vp_shape,repeats_location);
d_exponential_ve_median = nanmedian(d_exponential_ve_shape,repeats_location);
d_exponential_fp_median = nanmedian(d_exponential_fp_shape,repeats_location);

% Remove signleton repeats dimension
sz = size(d_exponential_ktrans_median);
if size(sz)>repeats_location
    sz(repeats_location) = [];
end
exponential_ktrans_error_std = reshape(exponential_ktrans_error_std,sz);
d_exponential_ktrans_error_std = reshape(d_exponential_ktrans_error_std,sz);
d_exponential_vp_error_std = reshape(d_exponential_vp_error_std,sz);
d_exponential_ve_error_std = reshape(d_exponential_ve_error_std,sz);
d_exponential_fp_error_std = reshape(d_exponential_fp_error_std,sz);

exponential_ktrans_average = reshape(exponential_ktrans_average,sz);
d_exponential_ktrans_average = reshape(d_exponential_ktrans_average,sz);
d_exponential_vp_average = reshape(d_exponential_vp_average,sz);
d_exponential_ve_average = reshape(d_exponential_ve_average,sz);
d_exponential_fp_average = reshape(d_exponential_fp_average,sz);

exponential_ktrans_median = reshape(exponential_ktrans_median,sz);
d_exponential_ktrans_median = reshape(d_exponential_ktrans_median,sz);
d_exponential_vp_median = reshape(d_exponential_vp_median,sz);
d_exponential_ve_median = reshape(d_exponential_ve_median,sz);
d_exponential_fp_median = reshape(d_exponential_fp_median,sz);
% Reduce by one since the repeats dimension was removed
toffset_location = toffset_location-1;

% Subtract out the true values to get the bias error
d_exponential_ktrans_error = bsxfun(@minus,d_exponential_ktrans_average,ktrans_list');
d_exponential_ktrans_error_percent = bsxfun(@rdivide,d_exponential_ktrans_error,ktrans_list');

if average_across_offset
    exponential_ktrans_error_std = nanmean(exponential_ktrans_error_std, toffset_location);
    d_exponential_ktrans_error_std = nanmean(d_exponential_ktrans_error_std, toffset_location);
    d_exponential_vp_error_std = nanmean(d_exponential_vp_error_std, toffset_location);
    d_exponential_ve_error_std = nanmean(d_exponential_ve_error_std, toffset_location);
    d_exponential_fp_error_std = nanmean(d_exponential_fp_error_std, toffset_location);

    exponential_ktrans_average = nanmean(exponential_ktrans_average, toffset_location);
    d_exponential_ktrans_average = nanmean(d_exponential_ktrans_average, toffset_location);
    d_exponential_vp_average = nanmean(d_exponential_vp_average, toffset_location);
    d_exponential_ve_average = nanmean(d_exponential_ve_average, toffset_location);
    d_exponential_fp_average = nanmean(d_exponential_fp_average, toffset_location);

    exponential_ktrans_median = nanmean(exponential_ktrans_median, toffset_location);
    d_exponential_ktrans_median = nanmean(d_exponential_ktrans_median, toffset_location);
    d_exponential_vp_median = nanmean(d_exponential_vp_median, toffset_location);
    d_exponential_ve_median = nanmean(d_exponential_ve_median, toffset_location);
    d_exponential_fp_median = nanmean(d_exponential_fp_median, toffset_location);
    
    d_exponential_ktrans_error = nanmean(d_exponential_ktrans_error, toffset_location);
    d_exponential_ktrans_error_percent = nanmean(d_exponential_ktrans_error_percent, toffset_location);
end