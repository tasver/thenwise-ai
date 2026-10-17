import argparse,pathlib
def main():
 p=argparse.ArgumentParser();s=p.add_subparsers(dest="cmd",required=True)
 t=s.add_parser("tts");t.add_argument("--text",required=True);t.add_argument("--reference",required=True);t.add_argument("--output",required=True);t.add_argument("--device",default="cuda")
 w=s.add_parser("whisper");w.add_argument("--input",required=True);w.add_argument("--output",required=True);w.add_argument("--device",default="cuda");w.add_argument("--model",default="large-v3")
 a=p.parse_args();pathlib.Path(a.output).parent.mkdir(parents=True,exist_ok=True)
 if a.cmd=="tts":
  import soundfile as sf
  from chatterbox.tts_turbo import ChatterboxTurboTTS
  m=ChatterboxTurboTTS.from_pretrained(device=a.device);y=m.generate(a.text,audio_prompt_path=a.reference)
  sf.write(a.output,y.squeeze().detach().cpu().numpy(),m.sr)
 else:
  from faster_whisper import WhisperModel
  m=WhisperModel(a.model,device=a.device,compute_type="float16")
  segs,_=m.transcribe(a.input)
  pathlib.Path(a.output).write_text("".join(f"{x.start:.3f}\t{x.end:.3f}\t{x.text.strip()}\n" for x in segs))
 print(a.output)
if __name__=="__main__":main()
