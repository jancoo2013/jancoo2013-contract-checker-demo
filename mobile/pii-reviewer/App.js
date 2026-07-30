import React, { useEffect, useState } from 'react';
import { Image, Pressable, SafeAreaView, ScrollView, StyleSheet, Text, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { pickReviewPack, saveReviewResult } from './src/androidPackIo';
import {
  CATEGORIES, addIssueTap, contentRect, displayBox, imagePoint, isComplete,
  newSession, setCategory, setPageIndex, setStatus, undoFinding,
} from './src/reviewerState';

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
  const [imageReady, setImageReady] = useState(false);
  const ready = view.width > 1 && view.height > 1;
  const uri = mode === 'source' ? page.sourceUri : page.derivativeUri;
  const rect = contentRect(view.width, view.height, page.width, page.height);
  useEffect(() => setImageReady(false), [page.imageId, uri, view.width, view.height]);
  return (
    <View
      style={styles.canvas}
      onLayout={(event) => setView(event.nativeEvent.layout)}
      onTouchEnd={(event) => {
        if (!imageReady) return;
        onTap(imagePoint(
          { x: event.nativeEvent.locationX, y: event.nativeEvent.locationY },
          view,
          { width: page.width, height: page.height },
        ));
      }}
    >
      {ready && <Image
        key={`${page.imageId}:${mode}:${Math.round(view.width)}x${Math.round(view.height)}`}
        source={{ uri }}
        resizeMode="contain"
        onLoad={() => setImageReady(true)}
        style={[styles.image, { left: rect.x, top: rect.y, width: rect.width, height: rect.height }]}
      />}
      {!imageReady && <View pointerEvents="none" style={styles.loading}><Text>Загрузка страницы…</Text></View>}
      {imageReady && page.findings.map((item, index) => (
        <View key={index} pointerEvents="none" style={[styles.finding, displayBox(item.box, view, page)]} />
      ))}
    </View>
  );
}
export default function App() {
  const [mode, setMode] = useState('source');
  const [session, setSession] = useState(null);
  const [message, setMessage] = useState('Выберите локальную папку review pack.');
  const page = session?.pages[session.pageIndex];
  const load = async () => {
    try {
      const pack = await pickReviewPack();
      if (pack) {
        setMode('source');
        setSession(newSession(pack.packKey, pack.pages));
        setMessage(`Загружено страниц: ${pack.pages.length}`);
      }
    } catch (error) {
      setMessage(error.message);
    }
  };
  const save = async () => {
    try {
      setMessage(`Сохранено: ${await saveReviewResult(session)}`);
    } catch (error) {
      setMessage(error.message);
    }
  };
  const choose = (category) => {
    setSession((current) => setCategory(current, category));
    setMode(category === 'missed_pii' ? 'source' : 'masked');
  };
  return (
    <SafeAreaView style={styles.screen}>
      <StatusBar style="dark" />
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.title}>PII Reviewer · Android</Text>
        <Pressable style={styles.primary} onPress={load}><Text>Выбрать review pack</Text></Pressable>
        <Text style={styles.note}>{message}</Text>
        {page && <>
          <Text style={styles.status}>Страница {session.pageIndex + 1}/{session.pages.length} · {page.imageId}</Text>
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
          <View style={styles.actions}>
            <Pressable disabled={session.pageIndex === 0}
              style={[styles.action, session.pageIndex === 0 && styles.disabled]}
              onPress={() => setSession((current) => setPageIndex(current, current.pageIndex - 1))}>
              <Text>Назад</Text>
            </Pressable>
            <Pressable disabled={session.pageIndex === session.pages.length - 1}
              style={[styles.action, session.pageIndex === session.pages.length - 1 && styles.disabled]}
              onPress={() => setSession((current) => setPageIndex(current, current.pageIndex + 1))}>
              <Text>Дальше</Text>
            </Pressable>
          </View>
          <Text style={styles.status}>Статус: {page.status} · ошибок: {page.findings.length}</Text>
          <Pressable disabled={!isComplete(session)} style={[styles.primary, !isComplete(session) && styles.disabled]} onPress={save}>
            <Text>Сохранить результат</Text>
          </Pressable>
        </>}
      </ScrollView>
    </SafeAreaView>
  );
}
const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: '#f2f4f7' },
  content: { padding: 16, gap: 12 },
  title: { fontSize: 22, fontWeight: '700' },
  note: { color: '#4b5563' },
  primary: { padding: 12, alignItems: 'center', backgroundColor: '#bfdbfe', borderRadius: 10 },
  tabs: { flexDirection: 'row', gap: 8 },
  tab: { flex: 1, padding: 10, alignItems: 'center', backgroundColor: '#e5e7eb', borderRadius: 10 },
  activeTab: { backgroundColor: '#c7d2fe' },
  tabText: { fontWeight: '600' },
  canvas: { height: 470, backgroundColor: '#d1d5db', borderRadius: 12, overflow: 'hidden' },
  image: { position: 'absolute' },
  loading: { ...StyleSheet.absoluteFillObject, alignItems: 'center', justifyContent: 'center' },
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
});