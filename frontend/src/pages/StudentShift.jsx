// src/pages/StudentShift.jsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const DateSelector = ({ date, day, isActive, onClick }) => (
  <button onClick={onClick} className={`min-w-[60px] rounded-xl p-2 text-center transition-all ${isActive ? 'bg-blue-600 text-white shadow-md' : 'bg-white text-gray-500 border border-gray-200 hover:bg-gray-50'}`}>
    <div className="text-xs">{day}</div>
    <div className="text-xl font-bold">{date}</div>
  </button>
);

const TimeSlot = ({ period, time, status, onStatusChange }) => (
  <div className={`bg-white p-4 rounded-2xl shadow-sm border flex items-center justify-between transition-colors ${status === 'blank' ? 'border-blue-300 ring-2 ring-blue-100' : 'border-gray-100'}`}>
    <div>
      <div className="text-xs text-gray-400 font-bold">{period}コマ目</div>
      <div className="text-lg font-bold text-gray-800">{time.start} <span className="text-sm font-normal text-gray-500">~ {time.end}</span></div>
    </div>
    <div className="flex bg-gray-100 rounded-lg p-1 gap-1">
      <button onClick={() => onStatusChange('available')} className={`w-12 h-10 rounded-md font-bold transition-all ${status === 'available' ? 'bg-emerald-500 text-white shadow-sm' : 'text-gray-400 hover:bg-gray-200'}`}>○</button>
      <button onClick={() => onStatusChange('unavailable')} className={`w-12 h-10 rounded-md font-bold transition-all ${status === 'unavailable' ? 'bg-red-500 text-white shadow-sm' : 'text-gray-400 hover:bg-gray-200'}`}>×</button>
    </div>
  </div>
);

export default function StudentShift() {
  const navigate = useNavigate();
  const [selectedDate, setSelectedDate] = useState('10');
  const [shiftData, setShiftData] = useState({ slot1: 'available', slot2: 'unavailable', slot3: 'blank', slot4: 'blank' });

  const handleStatusChange = (slotId, newStatus) => {
    setShiftData(prev => ({ ...prev, [slotId]: prev[slotId] === newStatus ? 'blank' : newStatus }));
  };

  return (
    <div className="min-h-screen bg-gray-100 flex justify-center p-4 font-sans">
      <div className="w-full max-w-[400px] bg-gray-50 rounded-[2rem] shadow-xl overflow-hidden border-4 border-white flex flex-col relative h-[800px]">
        <header className="bg-blue-800 text-white pt-10 pb-4 px-6 rounded-b-3xl shadow-md z-10 flex justify-between items-center">
          <button onClick={() => navigate('/')} className="text-sm bg-white/20 px-3 py-1 rounded-lg">← 戻る</button>
          <h1 className="text-lg font-bold">シフト入力</h1>
          <div className="w-8 h-8"></div>
        </header>

        <main className="flex-1 overflow-y-auto p-4 hide-scrollbar">
          <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
            <DateSelector date="10" day="月" isActive={selectedDate === '10'} onClick={() => setSelectedDate('10')} />
            <DateSelector date="11" day="火" isActive={selectedDate === '11'} onClick={() => setSelectedDate('11')} />
            <DateSelector date="12" day="水" isActive={selectedDate === '12'} onClick={() => setSelectedDate('12')} />
          </div>
          <div className="space-y-3">
            <TimeSlot period="1" time={{ start: '13:00', end: '14:20' }} status={shiftData.slot1} onStatusChange={(status) => handleStatusChange('slot1', status)} />
            <TimeSlot period="2" time={{ start: '14:30', end: '15:50' }} status={shiftData.slot2} onStatusChange={(status) => handleStatusChange('slot2', status)} />
            <TimeSlot period="3" time={{ start: '16:00', end: '17:20' }} status={shiftData.slot3} onStatusChange={(status) => handleStatusChange('slot3', status)} />
            <TimeSlot period="4" time={{ start: '17:30', end: '18:50' }} status={shiftData.slot4} onStatusChange={(status) => handleStatusChange('slot4', status)} />
          </div>
        </main>
        <footer className="bg-white p-4 border-t border-gray-100">
          <button onClick={() => alert('提出処理')} className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-4 rounded-xl shadow-lg transition-transform active:scale-95">提出する</button>
        </footer>
      </div>
    </div>
  );
}