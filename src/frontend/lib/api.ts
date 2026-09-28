export type RecordBase = { id:string; upperType:string; upperColor:string; lowerType:string; lowerColor:string; visibleMarks:string; accessories:string; dentalNotes:string; otherDescription:string; status:string; createdAt:string; updatedAt:string }
export type AnteRecord = RecordBase & { fullName:string; age:number|null; heightCm:number|null }
export type PostRecord = RecordBase & { incidentRef:string; estimatedHeightCm:number|null; extractionStatus:string }
export type Dashboard = { totals:{ missingPersons:number; unidentifiedPersons:number; pendingReview:number; reconciled:number }; recentActivity:Array<AnteRecord|PostRecord> }
export type AiStatus = { provider:string; reachable:boolean; localOnly:boolean; message?:string; models:{ text:{name:string;installed:boolean}; vision:{name:string;installed:boolean} } }
export type Evidence = { key:string; label:string; anteValue:string; postValue:string; similarity:number|null; result:'concordant'|'partial'|'contradictory'|'unknown'; weight:number }
export type Match = { rank:number; score:number; classification:string; evidenceCoverage:number; rationale:string; disclaimer:string; candidate:AnteRecord; evidence:Evidence[] }
export type MatchResponse = { postMortem:PostRecord; matches:Match[] }

export class ApiError extends Error { constructor(message:string, public code='REQUEST_FAILED', public details?:unknown){ super(message) } }
async function request<T>(path:string, init?:RequestInit):Promise<T>{
  const response=await fetch(`/backend${path}`,{...init,cache:'no-store',headers:{'content-type':'application/json',...init?.headers}})
  const body=await response.json().catch(()=>({}))
  if(!response.ok) throw new ApiError(body.error?.message||`Request failed (${response.status})`,body.error?.code,body.error?.details)
  return body.data as T
}
export const api={
  dashboard:()=>request<Dashboard>('/api/v1/dashboard'), ante:()=>request<AnteRecord[]>('/api/v1/ante-mortem'), post:()=>request<PostRecord[]>('/api/v1/post-mortem'), aiStatus:()=>request<AiStatus>('/api/v1/ai/status'),
  matches:(id:string)=>request<MatchResponse>(`/api/v1/post-mortem/${encodeURIComponent(id)}/matches?limit=3`),
  createAnte:(data:Record<string,unknown>)=>request<AnteRecord>('/api/v1/ante-mortem',{method:'POST',body:JSON.stringify(data)}),
  createPost:(data:Record<string,unknown>)=>request<PostRecord>('/api/v1/post-mortem',{method:'POST',body:JSON.stringify(data)}),
  fromImage:async(data:Record<string,unknown>)=>{const response=await fetch('/backend/api/v1/post-mortem/from-image',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(data)});const body=await response.json().catch(()=>({}));if(!response.ok)throw new ApiError(body.error?.message||'Image analysis failed',body.error?.code,body.error?.details);return body as {data:PostRecord;meta:{extraction:Record<string,unknown>;requiresHumanReview:boolean;rawImageStored:boolean}}},
}
