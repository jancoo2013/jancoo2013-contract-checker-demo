import React, { useMemo, useState } from 'react';
import { Pressable, SafeAreaView, ScrollView, StyleSheet, Text, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import {
  CATEGORIES,
  addTap,
  canonicalJsonl,
  contentRect,
  displayBox,
  imagePoint,
  newSession,
  setStatus,
  undoFinding,
} from './src/reviewerState';

const DEMO_PAGE = {
  imageId: 'SYNTH-P0001',
  sourceSha256: '1'.repeat(64),
  derivativeSha256: '2'.repeat(64),
  width: 1000,
  height: 1400,
};
const DEMO_MASKS = [[120, 155, 880, 235], [610, 1180, 900, 1255]];
const LABELS = {
  missed_pii: 'PII пропущены',
  incomplete_mask: 'Маска неполная',
  over_redaction: 'Закрыт полезный текст',
};

function PageCanvas({ mode, page, findings, firstPoint, onTap }) {
  const [view, setView] = useState({ width: 1, height: 1 });
  const rows = useMemo(() => Array.from({ length: 22 }, (_, index) => index), []);
  const boxes = mode === 'masked' ? DEMO_MASKS : [];
  const pageRect = contentRect(view.width, view.height, page.width, page.height);
  return (
    <View
      style={styles.canvas}
      onLayout={(event) => setView(event.nativeEvent.layout)}
      onTouchEnd={(event) => {
        const point = imagePoint(
          { x: event.nativeEvent.locationX, y: event.nativeEvent.locationY },
          view,
          { width: page.width, height: page.height },
        );
        onTap(point);
      }}
    >
      <View style={[styles.paper, pageRect]}>
        {rows.map((row) => <View key={row} style={[styles.textRow, { width: `${58 + (row % 5) * 7}%` }]} />)}
        <View style={styles.syntheticPii}><Text style={styles.syntheticPiiText}>פרטי צדדים 000000000</Text></View>
      </View>
      {boxes.map((box, index) => <View key={`mask-${index}`} pointerEvents="none" style={[styles.mask, displayBox(box, view, page)]} />)}
      {findings.map((finding, index) => <View key={`finding-${index}`} pointerEvents="none" style={[styles.finding, displayBox(finding.box, view, page)]} />)}
      {firstPoint && <View pointerEvents="none" style={[styles.point, {
        left: displayBox([firstPoint.x, firstPoint.y, firstPoint.x + 1, firstPoint.y + 1], view, page).left - 5,
        top: displayBox([firstPoint.x, firstPoint.y, firstPoint.x + 1, firstPoint.y + 1], view, page).top - 5,
      }]} />}
    </View>
  );
}

export default function App() {
  const [mode, setMode] = useState('source');
  const [session, setSession] = useState(() => newSession('a'.repeat(64), [DEMO_PAGE]));
  const page = session.pages[session.pageIndex];
  return (
    <SafeAreaView style={styles.screen}>
      <StatusBar style="dark" />
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>PII Reviewer · Android harness</Text>
        <Text style={styles.note}>Синтетический локальный экран. Никаких внешних вызовов.</Text>
        <View style={styles.tabs}>
          {['source', 'masked'].map((value) => <Pressable key={value} onPress={() => setMode(value)} style={[styles.tab, mode === value && styles.activeTab]}>
            <Text style={styles.tabText}>{value === 'source' ? 'Исходник' : 'После масок'}</Text>
          </Pressable>)}
        </View>
        <PageCanvas
          mode={mode}
          page={page}
          findings={page.findings}
          firstPoint={session.firstPoint}
          onTap={(point) => setSession((current) => addTap(current, point))}
        />
        <Text style={styles.help}>{session.firstPoint ? 'Выберите второй угол области.' : 'Выберите категорию и коснитесь двух углов ошибки.'}</Text>
        <View style={styles.categories}>
          {CATEGORIES.map((category) => <Pressable key={category} onPress={() => setSession((current) => ({ ...current, category }))} style={[styles.category, session.category === category && styles.activeCategory]}>
            <Text style={styles.categoryText}>{LABELS[category]}</Text>
          </Pressable>)}
        </View>
        <View style={styles.actions}>
          <Pressable style={styles.action} onPress={() => setSession((current) => undoFinding(current))}><Text>Отменить область</Text></Pressable>
          <Pressable disabled={page.findings.length > 0} style={[styles.action, page.findings.length > 0 && styles.disabled]} onPress={() => setSession((current) => setStatus(current, 'pass'))}><Text>Страница без ошибок</Text></Pressable>
        </View>
        <Text style={styles.status}>Статус: {page.status} · ошибок: {page.findings.length}</Text>
        <Text selectable style={styles.json}>{canonicalJsonl(session)}</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: '#f2f4f7' },
  content: { padding: 16, gap: 12 },
  title: { fontSize: 22, fontWeight: '700' },
  note: { color: '#4b5563' },
  tabs: { flexDirection: 'row', gap: 8 },
  tab: { flex: 1, padding: 10, alignItems: 'center', backgroundColor: '#e5e7eb', borderRadius: 10 },
  activeTab: { backgroundColor: '#c7d2fe' },
  tabText: { fontWeight: '600' },
  canvas: { height: 470, backgroundColor: '#d1d5db', borderRadius: 12, overflow: 'hidden' },
  paper: { position: 'absolute', backgroundColor: 'white', padding: 18, gap: 12 },
  textRow: { height: 5, backgroundColor: '#6b7280', alignSelf: 'flex-end' },
  syntheticPii: { position: 'absolute', top: 52, right: 16 },
  syntheticPiiText: { fontSize: 10, color: '#111827' },
  mask: { position: 'absolute', backgroundColor: 'black' },
  finding: { position: 'absolute', borderWidth: 3, borderColor: '#dc2626', backgroundColor: 'rgba(220,38,38,0.12)' },
  point: { position: 'absolute', width: 10, height: 10, borderRadius: 5, backgroundColor: '#dc2626' },
  help: { textAlign: 'center', fontWeight: '600' },
  categories: { gap: 8 },
  category: { padding: 10, borderRadius: 10, backgroundColor: '#e5e7eb' },
  activeCategory: { backgroundColor: '#fde68a' },
  categoryText: { textAlign: 'center' },
  actions: { flexDirection: 'row', gap: 8 },
  action: { flex: 1, padding: 10, borderRadius: 10, alignItems: 'center', backgroundColor: '#dbeafe' },
  disabled: { opacity: 0.4 },
  status: { fontWeight: '700' },
  json: { fontFamily: 'monospace', fontSize: 10, backgroundColor: 'white', padding: 10, borderRadius: 8 },
});
