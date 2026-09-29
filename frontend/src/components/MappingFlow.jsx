import { useMemo } from 'react'
import ReactFlow, { Background, Controls, MarkerType, ReactFlowProvider } from 'reactflow'
import 'reactflow/dist/style.css'

const FLOW = [
  { id: 'Unmapped', position: { x: 0, y: 40 } },
  { id: 'Proposed', position: { x: 180, y: 40 } },
  { id: 'AdminReviewed', position: { x: 370, y: 40 } },
  { id: 'Gating', position: { x: 580, y: 40 } },
  { id: 'Provisional', position: { x: 490, y: 180 } },
  { id: 'Rejected', position: { x: 700, y: 180 } },
  { id: 'ReVerification', position: { x: 490, y: 310 } },
  { id: 'Corroborated', position: { x: 360, y: 440 } },
  { id: 'Demoted', position: { x: 660, y: 440 } },
]

const EDGES = [
  ['Unmapped', 'Proposed'],
  ['Proposed', 'AdminReviewed'],
  ['AdminReviewed', 'Gating'],
  ['Gating', 'Provisional'],
  ['Gating', 'Rejected'],
  ['Provisional', 'ReVerification'],
  ['ReVerification', 'Corroborated'],
  ['ReVerification', 'Demoted'],
]

function FlowInner({ currentState }) {
  const nodes = useMemo(() => FLOW.map(n => ({
    id: n.id,
    position: n.position,
    data: { label: n.id },
    style: {
      borderRadius: 8,
      border: currentState === n.id ? '2px solid #3b82f6' : '1px solid rgba(255,255,255,0.12)',
      background: currentState === n.id ? '#1e3a5f' : '#131920',
      color: '#e2e8f0',
      fontSize: 11,
      fontWeight: currentState === n.id ? 700 : 500,
      width: 140,
      padding: '6px 4px',
    },
  })), [currentState])

  const edges = useMemo(() => EDGES.map(([s, t]) => ({
    id: `${s}->${t}`,
    source: s,
    target: t,
    markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14 },
    style: { stroke: 'rgba(148,163,184,0.5)' },
  })), [])

  return (
    <ReactFlow nodes={nodes} edges={edges} fitView panOnScroll={false} nodesDraggable={false} nodesConnectable={false}>
      <Background gap={18} color="rgba(255,255,255,0.04)" />
      <Controls showInteractive={false} />
    </ReactFlow>
  )
}

export default function MappingFlow({ currentState }) {
  return (
    <div style={{ height: 420, background: 'var(--bg)', borderRadius: 10, border: '1px solid var(--border)' }}>
      <ReactFlowProvider>
        <FlowInner currentState={currentState} />
      </ReactFlowProvider>
    </div>
  )
}
