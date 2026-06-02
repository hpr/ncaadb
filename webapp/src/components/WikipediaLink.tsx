import { Anchor } from '@mantine/core';

const WIKIPEDIA_W_BASE: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  borderRadius: 3,
  background: '#fff',
  color: '#000',
  fontFamily: "'Linux Libertine', 'Georgia', serif",
  fontWeight: 700,
  textDecoration: 'none',
  border: '1px solid #a7d7f9',
  lineHeight: 1,
  flexShrink: 0,
  fontFeatureSettings: '"ss05"',
};

export function WikipediaW({ qid, size = 20 }: { qid: string; size?: number }) {
  const style: React.CSSProperties = {
    ...WIKIPEDIA_W_BASE,
    width: size,
    height: size,
    fontSize: Math.round(size * 0.72),
  };

  return (
    <Anchor
      href={`https://www.wikidata.org/wiki/Special:GoToLinkedPage/en/${qid}`}
      target="_blank"
      rel="noopener noreferrer"
      style={style}
      onClick={(e: React.MouseEvent) => e.stopPropagation()}
    >
      W
    </Anchor>
  );
}
