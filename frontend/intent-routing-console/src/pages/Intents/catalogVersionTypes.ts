export type CatalogPageState =
  | { mode: 'version'; version: API.CatalogVersionListItem }
  | { mode: 'draft'; sourceVersion?: API.CatalogVersionListItem };

export type CatalogVersionDiffSectionKey =
  | 'added_intents'
  | 'removed_intents'
  | 'changed_intents'
  | 'added_examples'
  | 'removed_examples'
  | 'changed_examples';

export type CatalogVersionDiffSection = {
  key: CatalogVersionDiffSectionKey;
  title: string;
};
