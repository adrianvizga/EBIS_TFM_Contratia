
import { useState, useMemo, useCallback } from 'react';
import { useLanguage } from '../context/useLanguage';

export type ClauseRelationType =
  | "contradiccion"
  | "dependencia"
  | "duplicidad"
  | "referencia_a_clausula_ausente";

export interface ClauseRelation {
  id: string;
  type: ClauseRelationType;
  fromClauseId: string;
  fromClauseTitle: string;
  toClauseId: string | null;
  toClauseTitle?: string;
  severity: "alta" | "media" | "baja";
  description: string;
}

interface ClauseRelationsGraphProps {
  relations: ClauseRelation[];
}

interface NodeData {
  id: string;
  title: string;
  isMissing: boolean;
  connections: number;
}

const NODE_W = 152;
const NODE_H = 52;
const H_GAP = 65;
const V_GAP = 75;
const PAD = 55;
const MAX_COLS = 4;
const CORNER_R = 6;

const RELATION_COLORS: Record<ClauseRelationType, string> = {
  contradiccion: '#ef4444',
  dependencia: '#3b82f6',
  duplicidad: '#8b5cf6',
  referencia_a_clausula_ausente: '#f97316',
};

const RELATION_DASH: Record<ClauseRelationType, string> = {
  contradiccion: '',
  dependencia: '7,4',
  duplicidad: '',
  referencia_a_clausula_ausente: '4,5',
};

function bfsOrder(nodes: NodeData[], relations: ClauseRelation[]): NodeData[] {
  const adj = new Map<string, Set<string>>();
  nodes.forEach(n => adj.set(n.id, new Set()));
  relations.forEach(r => {
    const toId = r.toClauseId || `missing-${r.id}`;
    adj.get(r.fromClauseId)?.add(toId);
    if (adj.has(toId)) adj.get(toId)!.add(r.fromClauseId);
  });

  const sorted = [...nodes].sort((a, b) => b.connections - a.connections);
  const visited = new Set<string>();
  const result: NodeData[] = [];
  const queue: string[] = [];

  for (const seed of sorted) {
    if (visited.has(seed.id)) continue;
    queue.push(seed.id);
    visited.add(seed.id);

    while (queue.length > 0) {
      const id = queue.shift()!;
      const node = nodes.find(n => n.id === id);
      if (node) result.push(node);

      const neighbors = Array.from(adj.get(id) || [])
        .filter(nId => !visited.has(nId))
        .sort((a, b) => (adj.get(b)?.size || 0) - (adj.get(a)?.size || 0));
      for (const nId of neighbors) {
        if (!visited.has(nId)) {
          visited.add(nId);
          queue.push(nId);
        }
      }
    }
  }

  return result;
}

function buildElbowPath(
  fromX: number, fromY: number, fromRow: number, fromCol: number,
  toX: number, toY: number, toRow: number, toCol: number,
  channelOffset: number,
  fromPortOff: number = 0,
  toPortOff: number = 0,
): { path: string; labelX: number; labelY: number } {
  let fCx = fromX + NODE_W / 2;
  let fCy = fromY + NODE_H / 2;
  let tCx = toX + NODE_W / 2;
  let tCy = toY + NODE_H / 2;

  if (fromRow === toRow && fromCol !== toCol) {
    fCx += fromPortOff;
    tCx += toPortOff;
  } else if (fromCol === toCol && fromRow !== toRow) {
    fCy += fromPortOff;
    tCy += toPortOff;
  } else if (fromRow !== toRow && fromCol !== toCol) {
    fCx += fromPortOff;
    tCx += toPortOff;
  }

  let points: [number, number][];

  if (fromRow === toRow && fromCol === toCol) {
    return {
      path: `M ${fCx} ${fromY} L ${fCx} ${fromY - 15}`,
      labelX: fCx,
      labelY: fromY - 20,
    };
  }

  if (fromRow === toRow) {
    const channelY = fromY - V_GAP / 2 + channelOffset * 10 + toPortOff * 0.6;
    const exitY = fromY;
    const entryY = toY;

    points = [
      [fCx, exitY],
      [fCx, channelY],
      [tCx, channelY],
      [tCx, entryY],
    ];
  } else if (fromCol === toCol) {
    const side = fromCol < MAX_COLS / 2 ? 1 : -1;
    const channelX = fromX + (side > 0 ? NODE_W + H_GAP / 2 : -H_GAP / 2) + channelOffset * 10 * side + toPortOff * 0.6 * side;
    const exitX = fromX + (side > 0 ? NODE_W : 0);
    const entryX = toX + (side > 0 ? NODE_W : 0);

    points = [
      [exitX, fCy],
      [channelX, fCy],
      [channelX, tCy],
      [entryX, tCy],
    ];
  } else {
    const goingDown = toRow > fromRow;
    const routeY = goingDown
      ? fromY + NODE_H + (V_GAP * 0.45) + channelOffset * 10 + toPortOff * 0.6
      : toY + NODE_H + (V_GAP * 0.45) + channelOffset * 10 + fromPortOff * 0.6;

    const exitY = goingDown ? fromY + NODE_H : fromY;
    const entryY = goingDown ? toY : toY + NODE_H;

    points = [
      [fCx, exitY],
      [fCx, routeY],
      [tCx, routeY],
      [tCx, entryY],
    ];
  }

  const r = CORNER_R;
  let d = `M ${points[0][0]},${points[0][1]}`;

  for (let i = 1; i < points.length - 1; i++) {
    const prev = points[i - 1];
    const curr = points[i];
    const next = points[i + 1];

    const dx1 = curr[0] - prev[0];
    const dy1 = curr[1] - prev[1];
    const dx2 = next[0] - curr[0];
    const dy2 = next[1] - curr[1];

    const len1 = Math.sqrt(dx1 * dx1 + dy1 * dy1);
    const len2 = Math.sqrt(dx2 * dx2 + dy2 * dy2);
    if (len1 < 1 || len2 < 1) {
      d += ` L ${curr[0]},${curr[1]}`;
      continue;
    }

    const useR = Math.min(r, len1 / 2, len2 / 2);

    const bx = curr[0] - (dx1 / len1) * useR;
    const by = curr[1] - (dy1 / len1) * useR;
    const ax = curr[0] + (dx2 / len2) * useR;
    const ay = curr[1] + (dy2 / len2) * useR;

    const cross = dx1 * dy2 - dy1 * dx2;
    const sweep = cross > 0 ? 1 : 0;

    d += ` L ${bx},${by} A ${useR},${useR} 0 0,${sweep} ${ax},${ay}`;
  }

  d += ` L ${points[points.length - 1][0]},${points[points.length - 1][1]}`;

  const midPt = points.length >= 3
    ? { x: (points[1][0] + points[2][0]) / 2, y: (points[1][1] + points[2][1]) / 2 }
    : { x: (points[0][0] + points[points.length - 1][0]) / 2, y: (points[0][1] + points[points.length - 1][1]) / 2 };

  return { path: d, labelX: midPt.x, labelY: midPt.y };
}

export default function ClauseRelationsGraph({ relations }: ClauseRelationsGraphProps) {
  const { t } = useLanguage();
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [selectedRelation, setSelectedRelation] = useState<ClauseRelation | null>(null);

  const layout = useMemo(() => {
    const nodesMap = new Map<string, NodeData>();
    const connCount = new Map<string, number>();

    relations.forEach(rel => {
      connCount.set(rel.fromClauseId, (connCount.get(rel.fromClauseId) || 0) + 1);
      if (rel.toClauseId) connCount.set(rel.toClauseId, (connCount.get(rel.toClauseId) || 0) + 1);

      if (!nodesMap.has(rel.fromClauseId)) {
        nodesMap.set(rel.fromClauseId, {
          id: rel.fromClauseId,
          title: rel.fromClauseTitle,
          isMissing: false,
          connections: 0,
        });
      }
      if (rel.toClauseId) {
        if (!nodesMap.has(rel.toClauseId)) {
          nodesMap.set(rel.toClauseId, {
            id: rel.toClauseId,
            title: rel.toClauseTitle || rel.toClauseId,
            isMissing: false,
            connections: 0,
          });
        }
      } else {
        const missingId = `missing-${rel.id}`;
        nodesMap.set(missingId, { id: missingId, title: t('relations.missingClause'), isMissing: true, connections: 1 });
      }
    });

    nodesMap.forEach((node, id) => { node.connections = connCount.get(id) || node.connections; });

    const allNodes = Array.from(nodesMap.values());
    const ordered = bfsOrder(allNodes, relations);

    const cols = Math.min(MAX_COLS, Math.max(2, Math.ceil(Math.sqrt(ordered.length))));

    const positions = new Map<string, { x: number; y: number; row: number; col: number }>();
    ordered.forEach((node, i) => {
      const row = Math.floor(i / cols);
      const col = i % cols;
      const nodesInRow = Math.min(cols, ordered.length - row * cols);
      const rowIndent = (cols - nodesInRow) * (NODE_W + H_GAP) / 2;

      positions.set(node.id, {
        x: PAD + col * (NODE_W + H_GAP) + rowIndent,
        y: PAD + row * (NODE_H + V_GAP),
        row,
        col,
      });
    });

    type Side = 'top' | 'bottom' | 'left' | 'right';
    interface PreEdge {
      rel: ClauseRelation;
      fromId: string;
      toId: string;
      fromPos: { x: number; y: number; row: number; col: number };
      toPos: { x: number; y: number; row: number; col: number };
      fromSide: Side;
      toSide: Side;
    }

    const preEdges: PreEdge[] = [];
    for (const rel of relations) {
      const fromId = rel.fromClauseId;
      const toId = rel.toClauseId || `missing-${rel.id}`;
      const fromPos = positions.get(fromId);
      const toPos = positions.get(toId);
      if (!fromPos || !toPos) continue;

      let fromSide: Side, toSide: Side;
      if (fromPos.row === toPos.row && fromPos.col === toPos.col) {
        fromSide = 'top'; toSide = 'top';
      } else if (fromPos.row === toPos.row) {
        fromSide = 'top'; toSide = 'top';
      } else if (fromPos.col === toPos.col) {
        const s = fromPos.col < cols / 2 ? 'right' : 'left';
        fromSide = s as Side; toSide = s as Side;
      } else {
        const down = toPos.row > fromPos.row;
        fromSide = down ? 'bottom' : 'top';
        toSide = down ? 'top' : 'bottom';
      }
      preEdges.push({ rel, fromId, toId, fromPos, toPos, fromSide, toSide });
    }

    const portCounts = new Map<string, number>();
    for (const pe of preEdges) {
      const fk = `${pe.fromId}-${pe.fromSide}`;
      const tk = `${pe.toId}-${pe.toSide}`;
      portCounts.set(fk, (portCounts.get(fk) || 0) + 1);
      portCounts.set(tk, (portCounts.get(tk) || 0) + 1);
    }

    const PORT_SPACING = 16;
    const portNextIdx = new Map<string, number>();
    const channelUsage = new Map<string, number>();

    const edges = preEdges.map(pe => {
      const { rel, fromId, toId, fromPos, toPos, fromSide, toSide } = pe;

      const fk = `${fromId}-${fromSide}`;
      const fromTotal = portCounts.get(fk) || 1;
      const fromIdx = portNextIdx.get(fk) || 0;
      portNextIdx.set(fk, fromIdx + 1);
      const fromPortOff = (fromIdx - (fromTotal - 1) / 2) * PORT_SPACING;

      const tk = `${toId}-${toSide}`;
      const toTotal = portCounts.get(tk) || 1;
      const toIdx = portNextIdx.get(tk) || 0;
      portNextIdx.set(tk, toIdx + 1);
      const toPortOff = (toIdx - (toTotal - 1) / 2) * PORT_SPACING;

      let channelKey: string;
      if (fromPos.row === toPos.row) {
        channelKey = `sr-${fromPos.row}`;
      } else if (fromPos.col === toPos.col) {
        channelKey = `sc-${fromPos.col}`;
      } else {
        channelKey = `rg-${Math.min(fromPos.row, toPos.row)}-${Math.max(fromPos.row, toPos.row)}`;
      }
      const chOffset = channelUsage.get(channelKey) || 0;
      channelUsage.set(channelKey, chOffset + 1);

      const { path, labelX, labelY } = buildElbowPath(
        fromPos.x, fromPos.y, fromPos.row, fromPos.col,
        toPos.x, toPos.y, toPos.row, toPos.col,
        chOffset,
        fromPortOff,
        toPortOff,
      );

      return {
        rel,
        fromId,
        toId,
        path,
        labelX,
        labelY,
        color: RELATION_COLORS[rel.type],
        dash: RELATION_DASH[rel.type],
      };
    }).filter(Boolean) as Array<{
      rel: ClauseRelation; fromId: string; toId: string;
      path: string; labelX: number; labelY: number;
      color: string; dash: string;
    }>;

    let maxX = 0, maxY = 0;
    positions.forEach(p => {
      maxX = Math.max(maxX, p.x + NODE_W);
      maxY = Math.max(maxY, p.y + NODE_H);
    });

    return {
      nodes: ordered,
      positions,
      edges,
      svgW: maxX + PAD,
      svgH: maxY + PAD + 10,
    };
  }, [relations, t]);

  const getRelatedNodeIds = useCallback((nodeId: string) => {
    const ids = new Set<string>();
    relations.forEach(rel => {
      if (rel.fromClauseId === nodeId) ids.add(rel.toClauseId || `missing-${rel.id}`);
      if (rel.toClauseId === nodeId) ids.add(rel.fromClauseId);
    });
    return ids;
  }, [relations]);

  if (relations.length === 0) return null;

  return (
    <div className="space-y-5 w-full">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 px-1">
        {([
          { type: 'contradiccion' as ClauseRelationType, key: 'contradiction', dash: '' },
          { type: 'dependencia' as ClauseRelationType, key: 'dependency', dash: '7,4' },
          { type: 'duplicidad' as ClauseRelationType, key: 'duplication', dash: '' },
          { type: 'referencia_a_clausula_ausente' as ClauseRelationType, key: 'missingReference', dash: '4,5' },
        ]).map(item => (
          <div key={item.type} className="flex items-center gap-2">
            <svg width="28" height="10">
              <line x1="0" y1="5" x2="28" y2="5"
                stroke={RELATION_COLORS[item.type]} strokeWidth="3"
                strokeDasharray={item.dash} strokeLinecap="round"
              />
            </svg>
            <span className="text-xs font-medium text-dark-600 dark:text-dark-300">
              {t(`relations.${item.key}`)}
            </span>
          </div>
        ))}
      </div>

      <div className="bg-gradient-to-br from-white to-slate-50 dark:from-dark-800 dark:to-dark-900 rounded-2xl border border-slate-200 dark:border-dark-600 overflow-hidden">
        <svg
          width="100%"
          viewBox={`0 0 ${layout.svgW} ${layout.svgH}`}
          preserveAspectRatio="xMidYMid meet"
          className="block"
          style={{ minHeight: 260 }}
        >
          <defs>
            {Object.entries(RELATION_COLORS).map(([type, color]) => (
              <marker key={type} id={`arr-${type}`}
                markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                <path d="M1,1 L7,4 L1,7" fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
              </marker>
            ))}
            <linearGradient id="nodeFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#60a5fa" />
              <stop offset="100%" stopColor="#3b82f6" />
            </linearGradient>
            <linearGradient id="nodeFillHover" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#93c5fd" />
              <stop offset="100%" stopColor="#60a5fa" />
            </linearGradient>
            <linearGradient id="missingFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#fcd34d" />
              <stop offset="100%" stopColor="#f59e0b" />
            </linearGradient>
            <filter id="nodeShadow" x="-10%" y="-10%" width="120%" height="130%">
              <feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.12" />
            </filter>
          </defs>

          {layout.edges.map(({ rel, fromId, toId, path, labelX, labelY, color, dash }) => {
            const isConnected = hoveredNode && (hoveredNode === fromId || hoveredNode === toId);
            const isActive = selectedRelation?.id === rel.id;
            const dimmed = hoveredNode && !isConnected;

            return (
              <g key={rel.id}>
                <path d={path} fill="none" stroke="transparent" strokeWidth="16"
                  className="cursor-pointer"
                  onMouseEnter={() => setSelectedRelation(rel)}
                  onMouseLeave={() => setSelectedRelation(null)}
                />
                <path
                  d={path} fill="none" stroke={color}
                  strokeWidth={isActive ? 3 : 2}
                  strokeDasharray={dash}
                  strokeLinecap="round"
                  opacity={dimmed ? 0.12 : isActive ? 1 : 0.55}
                  markerEnd={`url(#arr-${rel.type})`}
                  className="transition-all duration-150 pointer-events-none"
                />
                {(isActive || isConnected) && (() => {
                  const labelText = t(`relations.${rel.type}`);
                  const labelW = Math.max(60, labelText.length * 5.4 + 16);
                  return (
                    <g>
                      <rect x={labelX - labelW / 2} y={labelY - 10} width={labelW} height="20"
                        rx="10" fill={color} opacity="0.92"
                      />
                      <text x={labelX} y={labelY + 4}
                        textAnchor="middle" fontSize="9" fontWeight="600" fill="white"
                        className="pointer-events-none select-none"
                      >
                        {labelText}
                      </text>
                    </g>
                  );
                })()}
              </g>
            );
          })}

          {layout.nodes.map(node => {
            const pos = layout.positions.get(node.id);
            if (!pos) return null;

            const isHovered = hoveredNode === node.id;
            const isRelated = hoveredNode ? getRelatedNodeIds(hoveredNode).has(node.id) : false;
            const dimmed = hoveredNode && !isHovered && !isRelated;

            const truncLen = 18;
            const displayTitle = node.title.length > truncLen
              ? node.title.substring(0, truncLen - 1) + '…'
              : node.title;

            const fillId = node.isMissing ? 'url(#missingFill)' : isHovered ? 'url(#nodeFillHover)' : 'url(#nodeFill)';

            return (
              <g key={node.id}
                onMouseEnter={() => setHoveredNode(node.id)}
                onMouseLeave={() => setHoveredNode(null)}
                className="cursor-pointer"
              >
                <title>{node.isMissing ? node.title : `Cláusula ${node.id}: ${node.title}`}</title>

                <rect
                  x={pos.x} y={pos.y} width={NODE_W} height={NODE_H}
                  rx={10} fill={fillId}
                  stroke={isHovered ? '#1d4ed8' : isRelated ? '#93c5fd' : 'rgba(255,255,255,0.15)'}
                  strokeWidth={isHovered ? 2.5 : isRelated ? 2 : 0.5}
                  filter="url(#nodeShadow)"
                  opacity={dimmed ? 0.25 : 1}
                  className="transition-all duration-150"
                />

                <text
                  x={pos.x + NODE_W / 2} y={pos.y + 21}
                  textAnchor="middle" fontSize="15" fontWeight="700" fill="white"
                  opacity={dimmed ? 0.25 : 1}
                  className="pointer-events-none select-none"
                >
                  {node.isMissing ? '⚠' : `Cl. ${node.id}`}
                </text>

                <text
                  x={pos.x + NODE_W / 2} y={pos.y + 38}
                  textAnchor="middle" fontSize="9.5" fontWeight="500"
                  fill="rgba(255,255,255,0.85)"
                  opacity={dimmed ? 0.25 : 1}
                  className="pointer-events-none select-none"
                >
                  {node.isMissing ? t('relations.missingClause') : displayTitle}
                </text>

                {node.connections > 1 && (
                  <>
                    <circle cx={pos.x + NODE_W - 6} cy={pos.y + 6} r="8"
                      fill="#1e40af" stroke="white" strokeWidth="1.5"
                      opacity={dimmed ? 0.25 : 1}
                    />
                    <text x={pos.x + NODE_W - 6} y={pos.y + 9.5}
                      textAnchor="middle" fontSize="9" fontWeight="700" fill="white"
                      opacity={dimmed ? 0.25 : 1}
                      className="pointer-events-none select-none"
                    >
                      {node.connections}
                    </text>
                  </>
                )}
              </g>
            );
          })}
        </svg>
      </div>

      {selectedRelation && (
        <div className={`rounded-xl p-4 border shadow transition-all duration-150 ${selectedRelation.severity === 'alta'
          ? 'bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800'
          : selectedRelation.severity === 'media'
            ? 'bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800'
            : 'bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800'
          }`}>
          <div className="flex items-start gap-3">
            <span className={`px-2.5 py-1 rounded-full text-xs font-bold whitespace-nowrap ${selectedRelation.severity === 'alta' ? 'bg-red-500 text-white' :
              selectedRelation.severity === 'media' ? 'bg-amber-500 text-white' :
                'bg-blue-500 text-white'
              }`}>
              {t(`relations.severity.${selectedRelation.severity}`)}
            </span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-semibold text-sm text-dark-900 dark:text-white">
                  {t(`relations.${selectedRelation.type}`)}
                </span>
                <span className="text-xs text-dark-500 dark:text-dark-400">
                  Cl. {selectedRelation.fromClauseId} → {selectedRelation.toClauseId ? `Cl. ${selectedRelation.toClauseId}` : t('relations.missingClause')}
                </span>
              </div>
              <p className="text-dark-700 dark:text-dark-300 text-sm mt-1.5 leading-relaxed">
                {selectedRelation.description}
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-3">
        <h3 className="text-lg font-semibold text-dark-900 dark:text-white">
          {t('relations.detailedList')}
        </h3>
        <div className="grid gap-2.5">
          {relations.map((rel) => {
            const borderColor =
              rel.type === 'contradiccion' ? 'border-l-red-500' :
                rel.type === 'dependencia' ? 'border-l-blue-500' :
                  rel.type === 'duplicidad' ? 'border-l-purple-500' : 'border-l-orange-500';

            return (
              <div key={rel.id}
                className={`bg-white dark:bg-dark-800 rounded-xl p-4 border-l-4 shadow-sm hover:shadow-md transition-shadow ${borderColor}`}
              >
                <div className="flex items-start gap-3">
                  <span className={`px-2 py-1 rounded-full text-xs font-semibold whitespace-nowrap ${rel.severity === 'alta' ? 'bg-red-500 text-white' :
                    rel.severity === 'media' ? 'bg-amber-500 text-white' :
                      'bg-blue-500 text-white'
                    }`}>
                    {t(`relations.severity.${rel.severity}`)}
                  </span>
                  <div className="flex-1 min-w-0">
                    <h4 className="font-semibold text-dark-900 dark:text-white text-sm">
                      {t(`relations.${rel.type}`)}
                    </h4>
                    <p className="text-dark-500 dark:text-dark-400 text-xs mt-0.5">
                      Cl. {rel.fromClauseId}: {rel.fromClauseTitle} → {rel.toClauseId ? `Cl. ${rel.toClauseId}: ${rel.toClauseTitle}` : t('relations.missingClause')}
                    </p>
                    <p className="text-dark-700 dark:text-dark-300 text-sm mt-2 leading-relaxed">
                      {rel.description}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
