/** Optional host integration, not the dependency-free demo runtime.
 * Requires React and @puckeditor/core from the host application's locked toolchain.
 * No Puck Cloud dependency. Compilation/integration is a separate release gate.
 */
import React from 'react';
import { Puck, type Config, type Data } from '@puckeditor/core';
import '@puckeditor/core/puck.css';

export type PageKind = 'cover' | 'abstract' | 'contents' | 'chapter' | 'method'
  | 'architecture' | 'results' | 'matrix' | 'timeline' | 'equations'
  | 'references' | 'figure' | 'table' | 'glossary' | 'appendix'
  | 'limitations' | 'reproducibility' | 'conclusion';
export interface Page {
  id: string; kind: PageKind; title: string; body: string;
  art: number; blur: number; mermaid: string;
}
export interface Document {
  version: 2; title: string; subtitle: string; author: string; date: string;
  format: 'portrait' | 'landscape';
  theme: { accent: string; ink: string; paper: string; font: string };
  pages: Page[];
}
type Props = { DocumentPage: Omit<Page, 'id'> };
interface AdapterProps {
  document: Document;
  validate: (candidate: unknown) => Document;
  renderPage: (page: Page, document: Document) => React.ReactElement;
  onPublish: (document: Document) => void | Promise<void>;
}
const kinds: PageKind[] = ['cover','abstract','contents','chapter','method','architecture',
  'results','matrix','timeline','equations','references','figure','table','glossary',
  'appendix','limitations','reproducibility','conclusion'];

export function DocumentEditor({ document, validate, renderPage, onPublish }: AdapterProps) {
  const checked = validate(document);
  // Metadata and brand are held outside the layout canvas. No arbitrary HTML component.
  const config: Config<Props> = {
    components: {
      DocumentPage: {
        label: 'Dokumentseite',
        fields: {
          kind: { type: 'select', options: kinds.map(value => ({ label: value, value })) },
          title: { type: 'text' },
          body: { type: 'textarea' },
          art: { type: 'number', min: 0, max: 63 },
          blur: { type: 'number', min: 0, max: 12 },
          mermaid: { type: 'textarea' },
        },
        defaultProps: { kind: 'chapter', title: 'Neues Kapitel', body: '', art: 0, blur: 0, mermaid: '' },
        render: props => renderPage({
          id: props.id, kind: props.kind, title: props.title, body: props.body,
          art: props.art, blur: props.blur, mermaid: props.mermaid,
        }, checked),
      },
    },
  };
  const data: Data<Props> = {
    root: { props: {} },
    content: checked.pages.map(page => ({ type: 'DocumentPage', props: page })),
  };
  return <Puck config={config} data={data} onPublish={async next => {
    const candidate = validate({ ...checked, pages: next.content.map(item => {
      if (item.type !== 'DocumentPage') throw new Error('Unknown component');
      const { id, kind, title, body, art, blur, mermaid } = item.props;
      return { id, kind, title, body, art, blur, mermaid };
    }) });
    await onPublish(candidate);
  }} />;
}
