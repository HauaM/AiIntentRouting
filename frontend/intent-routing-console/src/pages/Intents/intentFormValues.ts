export type IntentFormMode = 'create' | 'edit';

export type IntentFormValues = {
  intent_id: string;
  domain: string;
  display_name: string;
  description: string;
  route_key: string;
  status?: 'draft' | 'active' | 'deprecated';
  include_keywords?: string[];
  exclude_keywords?: string[];
};

export type ExampleFormValues = {
  example_type: 'positive' | 'negative';
  text_raw: string;
  source: string;
  test_case_id?: string;
};

export const buildIntentFormInitialValues = (
  mode: IntentFormMode,
  intent?: API.Intent,
): Partial<IntentFormValues> => {
  if (mode === 'edit' && intent) {
    return {
      intent_id: intent.intent_id,
      domain: intent.domain,
      display_name: intent.display_name,
      description: intent.description,
      route_key: intent.route_key,
      status: intent.status as IntentFormValues['status'],
      include_keywords: intent.include_keywords,
      exclude_keywords: intent.exclude_keywords,
    };
  }

  return {
    include_keywords: [],
    exclude_keywords: [],
  };
};

export const buildExampleFormInitialValues = (): Partial<ExampleFormValues> => ({
  example_type: 'positive',
  source: 'admin_ui',
});
