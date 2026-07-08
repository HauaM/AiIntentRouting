export type ServiceFormValues = {
  service_id: string;
  display_name: string;
  environment: string;
  default_threshold_preset: API.ThresholdPreset;
  max_input_tokens: number | null;
};

export const serviceFormInitialValues: Pick<
  ServiceFormValues,
  'environment' | 'default_threshold_preset' | 'max_input_tokens'
> = {
  environment: 'dev',
  default_threshold_preset: 'balanced',
  max_input_tokens: 256,
};

export const toServiceCreateRequest = (
  values: ServiceFormValues,
): API.ServiceCreateRequest => ({
  service_id: values.service_id.trim(),
  display_name: values.display_name.trim(),
  environment: values.environment.trim(),
  default_threshold_preset: values.default_threshold_preset,
  max_input_tokens: Number(
    values.max_input_tokens ?? serviceFormInitialValues.max_input_tokens,
  ),
});
