export type ServiceFormValues = {
  service_id: string;
  display_name: string;
  max_input_tokens: number | null;
};

export const serviceFormInitialValues: Pick<ServiceFormValues, 'max_input_tokens'> = {
  max_input_tokens: 256,
};

export const toServiceCreateRequest = (
  values: ServiceFormValues,
): API.ServiceCreateRequest => ({
  service_id: values.service_id.trim(),
  display_name: values.display_name.trim(),
  max_input_tokens: Number(
    values.max_input_tokens ?? serviceFormInitialValues.max_input_tokens,
  ),
});
