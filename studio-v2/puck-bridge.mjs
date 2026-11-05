/** Pure data bridge. No cloud-client, eval, browser storage, model SDK or codegen. */
const rootFields = ['title', 'subtitle', 'author', 'date', 'format', 'theme'];
const pageFields = ['id', 'kind', 'title', 'body', 'art', 'blur', 'mermaid'];
export function toPuck(document, validate) {
  if (typeof validate !== 'function') throw new TypeError('A document validator is required');
  const doc = validate(structuredClone(document));
  return {
    root: { props: Object.fromEntries(rootFields.map(key => [key, doc[key]])) },
    content: doc.pages.map(page => ({ type: 'DocumentPage', props: structuredClone(page) })),
  };
}
export function fromPuck(data, validate) {
  if (typeof validate !== 'function') throw new TypeError('A document validator is required');
  if (!data || !data.root || !data.root.props || !Array.isArray(data.content)) throw new TypeError('Invalid Puck data');
  if (data.zones && Object.keys(data.zones).length) throw new TypeError('Nested zones are not supported by this document adapter');
  if (Object.keys(data.root.props).some(key => !rootFields.includes(key))) throw new TypeError('Unknown root property');
  const pages = data.content.map(item => {
    if (!item || item.type !== 'DocumentPage' || !item.props || Object.keys(item.props).some(key => !pageFields.includes(key))) {
      throw new TypeError('Only catalogued DocumentPage components are allowed');
    }
    return structuredClone(item.props);
  });
  return validate({ version: 2, ...structuredClone(data.root.props), pages });
}
