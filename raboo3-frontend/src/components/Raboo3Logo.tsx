'use client';

type Props = {
  size?: number;          // total square size (px)
  gapPct?: number;        // gap percentage between tiles
  radiusPct?: number;     // corner radius percentage
  colors?: [string,string,string,string]; // TL, TR, BL, BR
};

/* tiny color helper */
function shade(hex:string, amt:number){
  const n = parseInt(hex.replace('#',''),16);
  const r=(n>>16)&255;
  const g=(n>>8)&255;
  const b=n&255;
  const adj=(v:number)=>Math.max(0,Math.min(255,v+amt));
  const h=(v:number)=>v.toString(16).padStart(2,'0');
  return '#'+h(adj(r))+h(adj(g))+h(adj(b));
}

// Helper function to render one quad
function renderQuad(
  x: number,
  y: number,
  fill: string,
  cell: number,
  r: number
) {
  return (
    <g key={`${x}-${y}`} transform={`translate(${x},${y})`}>
      {/* soft drop shadow */}
      <rect x={4} y={6} width={cell} height={cell} rx={r} fill="rgba(0,0,0,.12)" />
      {/* tile with subtle radial/linear blend */}
      <defs>
        <linearGradient id={`g-${x}-${y}`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor={shade(fill, 18)} />
          <stop offset="100%" stopColor={shade(fill, -6)} />
        </linearGradient>
      </defs>
      <rect width={cell} height={cell} rx={r} fill={`url(#g-${x}-${y})`} />
    </g>
  );
}

export default function Raboo3Logo({
  size = 120,
  gapPct = 0.10,
  radiusPct = 0.22,
  colors = ['#154F3C', '#4A8D71', '#3A7E64', '#97C9AB'],
}: Props) {
  const gap = size * gapPct;
  const cell = (size - gap) / 2;
  const r = cell * radiusPct;

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label="Raboo3 logo">
      {renderQuad(0, 0, colors[0], cell, r)}
      {renderQuad(cell + gap, 0, colors[1], cell, r)}
      {renderQuad(0, cell + gap, colors[2], cell, r)}
      {renderQuad(cell + gap, cell + gap, colors[3], cell, r)}
    </svg>
  );
}
