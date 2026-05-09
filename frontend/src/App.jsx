import React, { useState, useEffect, createContext, useContext } from 'react';
import { MapContainer, TileLayer, GeoJSON, useMapEvents, useMap } from 'react-leaflet';
import axios from 'axios';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';


const api = axios.create({ baseURL: 'http://127.0.0.1:8000' });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});


const AuthContext = createContext();
const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('token'));
  
  const login = async (username, password) => {
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);
    const res = await api.post('/token', params);
    localStorage.setItem('token', res.data.access_token);
    setToken(res.data.access_token);
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
  };

  return (
    <AuthContext.Provider value={{ token, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};


function MapAutoCenter({ detectionData }) {
  const map = useMap();
  useEffect(() => {
    if (detectionData && detectionData.features && detectionData.features.length > 0) {
      const firstFeature = detectionData.features[0];
      const [lon, lat] = firstFeature.geometry.coordinates;
      
      map.setView([lat, lon], 14); 
      console.log("Peta otomatis pindah ke lokasi citra:", lat, lon);
    }
  }, [detectionData, map]);
  return null;
}


function WebGIS() {
  const { token, login, logout } = useContext(AuthContext);
  const [geoData, setGeoData] = useState(null); 
  const [detectionData, setDetectionData] = useState(null); 
  const [authForm, setAuthForm] = useState({ username: '', password: '' });
  const [formData, setFormData] = useState({ id: null, nama: '', lat: '', lon: '' });
  const [isEdit, setIsEdit] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');

  const fetchData = async () => {
    try {
      const resManual = await api.get('/facilities/geojson');
      setGeoData(resManual.data);
      
      const resAi = await api.get('/detection/geojson');
      setDetectionData(resAi.data);
    } catch (err) {
      console.error("Gagal sinkronisasi data:", err);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleAuth = async (e) => {
    e.preventDefault();
    try {
      await login(authForm.username, authForm.password);
      setStatusMsg("✅ Login Admin Berhasil");
      setTimeout(() => setStatusMsg(''), 3000);
    } catch (err) {
      alert("Login Gagal! Cek kredensial kamu.");
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.lat || !formData.lon) return alert("Pilih titik di peta dulu!");
    
    try {
      await api.post('/facilities', formData);
      setStatusMsg(isEdit ? "✅ Data Diupdate" : "🚀 Data Disimpan");
      setFormData({ id: null, nama: '', lat: '', lon: '' });
      setIsEdit(false);
      fetchData();
      setTimeout(() => setStatusMsg(''), 3000);
    } catch (err) {
      alert("Akses Ditolak!");
    }
  };

  function MapClick() {
    useMapEvents({
      click(e) {
        if (token) {
          setFormData(prev => ({ ...prev, lat: e.latlng.lat, lon: e.latlng.lng }));
          setIsEdit(false);
        }
      },
    });
    return null;
  }

  window.triggerEdit = (id, nama, lat, lon) => {
    setFormData({ id, nama, lat, lon });
    setIsEdit(true);
  };

  return (
    <div className="flex flex-col h-screen w-full bg-slate-50 font-sans">
      <header className="bg-indigo-950 text-white p-4 flex justify-between items-center shadow-md z-[1000]">
        <h1 className="font-bold text-xl tracking-tight">ITERA SPATIAL AI <span className="text-emerald-400 text-xs">v1.0</span></h1>
        <div className="flex gap-2">
          {!token ? (
            <form onSubmit={handleAuth} className="flex gap-2">
              <input type="text" placeholder="User" className="px-2 py-1 rounded text-black text-sm" onChange={e => setAuthForm({...authForm, username: e.target.value})} />
              <input type="password" placeholder="Pass" className="px-2 py-1 rounded text-black text-sm" onChange={e => setAuthForm({...authForm, password: e.target.value})} />
              <button className="bg-emerald-600 px-4 py-1 rounded text-sm font-bold hover:bg-emerald-700">LOGIN</button>
            </form>
          ) : (
            <button onClick={logout} className="bg-rose-600 px-4 py-1 rounded text-sm font-bold">LOGOUT</button>
          )}
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {token && (
          <aside className="w-80 bg-white shadow-2xl p-6 z-[999] overflow-y-auto border-r">
            <h2 className="font-black text-indigo-900 mb-6 border-b-4 border-indigo-100 pb-2 uppercase italic text-sm">
              {isEdit ? '🛠️ Edit Fasilitas' : '➕ Tambah Fasilitas'}
            </h2>
            <form onSubmit={handleSubmit} className="flex flex-col gap-6">
              <div>
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Nama Objek</label>
                <input 
                  type="text" 
                  className="w-full border-b-2 p-2 outline-none focus:border-indigo-500 font-medium"
                  value={formData.nama}
                  onChange={e => setFormData({...formData, nama: e.target.value})}
                  placeholder="Misal: Gedung E"
                  required
                />
              </div>
              <div className="bg-indigo-50 p-4 rounded-xl border border-indigo-100">
                <p className="text-[9px] font-bold text-indigo-400 mb-1">KOORDINAT TERPILIH</p>
                <p className="text-xs font-mono text-indigo-900">
                  {formData.lat ? `${formData.lat.toFixed(6)}, ${formData.lon.toFixed(6)}` : '⚠️ Klik pada peta...'}
                </p>
              </div>
              <button className="bg-indigo-600 text-white font-black py-3 rounded-xl shadow-lg hover:bg-indigo-700 transition-all">
                {isEdit ? 'UPDATE DATA' : 'POST KE DATABASE'}
              </button>
              {statusMsg && <p className="text-center text-xs font-bold text-emerald-600 bg-emerald-50 py-2 rounded-lg">{statusMsg}</p>}
            </form>
          </aside>
        )}

        <main className="flex-1 relative">
          <MapContainer center={[-5.357, 105.314]} zoom={15} className="h-full w-full">
            <TileLayer url="https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png" />
            
            <MapClick />
           
            <MapAutoCenter detectionData={detectionData} />
            
           
            {geoData && (
              <GeoJSON 
                data={geoData} 
                pointToLayer={(f, l) => L.circleMarker(l, { 
                  radius: 9, fillColor: "#ef4444", color: "#fff", weight: 3, fillOpacity: 1 
                })}
                onEachFeature={(f, layer) => layer.bindPopup(`
                  <div class="p-2">
                    <b class="text-indigo-900">${f.properties.nama}</b><br/>
                    <button class="w-full mt-2 bg-slate-100 text-indigo-700 py-1 rounded text-[10px] font-bold" 
                      onclick="window.triggerEdit(${f.id}, '${f.properties.nama}', ${f.geometry.coordinates[1]}, ${f.geometry.coordinates[0]})">
                      EDIT DATA
                    </button>
                  </div>
                `)}
              />
            )}

           
            {detectionData && (
              <GeoJSON 
                data={detectionData} 
                pointToLayer={(f, l) => L.circleMarker(l, { 
                  radius: 7, fillColor: "#3b82f6", color: "#fff", weight: 2, fillOpacity: 0.9 
                })}
                onEachFeature={(f, layer) => layer.bindPopup(`
                  <div class="p-1 text-center">
                    <span class="bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full text-[8px] font-black uppercase">AI Detected</span><br/>
                    <b class="text-sm block mt-1">${f.properties.nama}</b>
                    <span class="text-[10px] text-slate-400 italic">Conf: ${f.properties.confidence}</span>
                  </div>
                `)}
              />
            )}
          </MapContainer>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <WebGIS />
    </AuthProvider>
  );
}