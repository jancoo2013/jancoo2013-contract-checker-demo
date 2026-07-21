import React, { useState } from 'react';
import { Pressable, SafeAreaView, ScrollView, StyleSheet, Text, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import {
  CATEGORIES, addIssueTap, canonicalJsonl, contentRect, displayBox, imagePoint,
  newSession, setCategory, setStatus, undoFinding,
} from './src/reviewerState';
const LINES = Array.from({ length: 18 }, (_, index) => {
  const y = 110 + index * 64;
  return { id: `line-${index + 1}`, box: [120, y, 880 - (index % 4) * 70, y + 24] };
});
const PAGE = {
  imageId: 'SYNTH-P0001', sourceSha256: '1'.repeat(64), derivativeSha256: '2'.repeat(64),
  width: 1000, height: 1400, reviewRegions: LINES,
  candidateMasks: [
    { id: 'mask-1', box: [120, 110, 880, 174] },
    { id: 'mask-2', box: [610, 1134, 900, 1210] },
  ],
};
const LABELS = {
  missed_pii: 'PII пропущены',
  incomplete_mask: 'Маска неполная',
  over_redaction: 'Закрыт полезный текст',
};
const HELP = {
  missed_pii: 'Коснитесь строки, где остались видимые персональные данные.',
  incomplete_mask: 'Коснитесь существующей неполной маски.',
  over_redaction: 'Коснитесь существующей лишней маски.',
};
function PageCanvas({ mode, page, onTap }) {
  const [view, setView] = useState({ width: 1, height: 1 });
  return (
    <View
      style={styles.canvas}
      onLayout={(event) => setView(event.nativeEvent.layout)}
      onTouchEnd={(event) => onTap(imagePoint(
        { x: event.nativeEvent.locationX, y: event.nativeEvent.locationY },
        view,
        { width: page.width, height: page.height },
      ))}
    >
      <View style={[styles.paper, contentRect(view.width, view.height, page.width, page.height)]} />
      {page.reviewRegions.map((item) => (
        <View key={item.id} pointerEvents="none" style={[styles.textRow, displayBox(item.box, view, page)]} />
      ))}
      {mode === 'masked' && page.candidateMasks.map((item) => (
        <View key={item.id} pointerEvents="none" style={[styles.mask, displayBox(item.box, view, page)]} />
      ))}
      {page.findings.map((item, index) => (
        <View key={index} pointerEvents="none" style={[styles.finding, displayBox(item.box, view, page)]} />
      ))}
    </View>
  );
}
export default function App() {
  const [mode, setMode] = useState('source');
  const [session, setSession] = useState(() => newSession('a'.repeat(64), [PAGE]));
  const page = session.pages[session.pageIndex];
  const choose = (category) => {
    setSession((current) => setCategory(current, category));
    setMode(category === 'missed_pii' ? 'source' : 'masked');
  };
  return (
    <SafeAreaView style={styles.screen}>
      <StatusBar style="dark" />
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>PII Reviewer · Android harness</Text>
        <Text style={styles.note}>Проверяющий отмечает ошибку, но не рисует и не исправляет маску.</Text>
        <View style={styles.tabs}>
          {['source', 'masked'].map((value) => (
            <Pressable key={value} onPress={() => setMode(value)} style={[styles.tab, mode === value && styles.activeTab]}>
              <Text style={styles.tabText}>{value === 'source' ? 'Исходник' : 'После масок'}</Text>
            </Pressable>
          ))}
        </View>
        <PageCanvas mode={mode} page={page} onTap={(point) => setSession((current) => addIssueTap(current, point))} />
        <Text style={styles.help}>{HELP[session.category]}</Text>
        {session.selectionError && <Text style={styles.error}>{session.selectionError}</Text>}
        <View style={styles.categories}>
          {CATEGORIES.map((category) => (
            <Pressable key={category} onPress={() => choose(category)}
              style={[styles.category, session.category === category && styles.activeCategory]}>
              <Text style={styles.categoryText}>{LABELS[category]}</Text>
            </Pressable>
          ))}
        </View>
        <View style={styles.actions}>
          <Pressable style={styles.action} onPress={() => setSession((current) => undoFinding(current))}>
            <Text>Отменить отметку</Text>
          </Pressable>
          <Pressable disabled={page.findings.length > 0}
            style={[styles.action, page.findings.length > 0 && styles.disabled]}
            onPress={() => setSession((current) => setStatus(current, 'pass'))}>
            <Text>Страница чистая</Text>
          </Pressable>
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
  paper: { position: 'absolute', backgroundColor: 'white' },
  textRow: { position: 'absolute', backgroundColor: '#6b7280' },
  mask: { position: 'absolute', backgroundColor: 'black' },
  finding: { position: 'absolute', borderWidth: 3, borderColor: '#dc2626', backgroundColor: 'rgba(220,38,38,0.12)' },
  help: { textAlign: 'center', fontWeight: '600' },
  error: { textAlign: 'center', color: '#b91c1c' },
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
