import { useCallback, useEffect, useReducer, useState } from "react";
import type { Verdict } from "./domain";
import { Hearing } from "./screens/Hearing";
import { QBRView } from "./screens/QBRView";
import { RunBoard } from "./screens/RunBoard";
import { SealedArchive } from "./screens/SealedArchive";
import { SealFlow } from "./screens/SealFlow";
import { playSound, restoreSoundPreference } from "./sound";
import type { AppState } from "./store";
import { casesRemaining, loadPersisted, persist, reduce, seedState, stageOf } from "./store";
import { withTransition } from "./vt";

const CAVEATS = [
  "Activity data from the Microsoft 365 Copilot usage report; no message content is accessed.",
  "GitHub last-activity is retained ~90 days by the vendor; sealed snapshots preserve history beyond that window.",
];

type Route =
  | { name: "board" }
  | { name: "hearing"; clientId: string }
  | { name: "seal"; clientId: string }
  | { name: "qbr"; clientId: string; quarter: string }
  | { name: "archive"; clientId: string };

export function App({ initial }: { initial?: AppState }) {
  // Persistence is active only without an explicit initial state, so
  // stories and tests stay deterministic while the real app survives reload.
  const persistent = initial === undefined;
  const [state, dispatch] = useReducer(reduce, undefined, () =>
    initial ?? loadPersisted() ?? seedState(),
  );
  useEffect(() => {
    if (persistent) persist(state);
  }, [persistent, state]);
  // restore the opt-in sound preference under the same discipline
  useEffect(() => {
    if (persistent) restoreSoundPreference();
  }, [persistent]);

  // Solo path (blueprint round 4): one client → straight to the Hearing.
  const [route, setRoute] = useState<Route>(() =>
    state.clients.length === 1
      ? { name: "hearing", clientId: state.clients[0].id }
      : { name: "board" },
  );

  const openClient = useCallback(
    (clientId: string) => {
      // Sealed periods are read-only: a sealed tile opens the archived
      // report (the frozen snapshot), never an editable hearing.
      playSound("shuffle"); // the case file slides across the desk
      withTransition(() => {
        if (stageOf(state, clientId) === "sealed") {
          setRoute({ name: "archive", clientId });
        } else {
          setRoute({ name: "hearing", clientId });
        }
      });
    },
    [state],
  );

  if (route.name === "board") {
    return (
      <RunBoard
        state={state}
        onOpenClient={openClient}
        onOpenQBR={(clientId, quarter) => setRoute({ name: "qbr", clientId, quarter })}
        firstRunPersistent={persistent}
        soundPersistent={persistent}
      />
    );
  }

  const client = state.clients.find((c) => c.id === route.clientId)!;

  if (route.name === "qbr") {
    return (
      <QBRView
        state={state}
        clientId={client.id}
        quarter={route.quarter}
        onBack={() => setRoute({ name: "board" })}
      />
    );
  }

  if (route.name === "archive") {
    const snapshot = state.sealed.find(
      (s) => s.clientId === client.id && s.period === state.period,
    );
    if (!snapshot)
      return (
        <RunBoard state={state} onOpenClient={openClient} firstRunPersistent={persistent} />
      );
    return (
      <SealedArchive
        snapshot={snapshot}
        clientName={client.name}
        mspName="Your MSP"
        caveats={CAVEATS}
        onBack={() => setRoute({ name: "board" })}
      />
    );
  }

  if (route.name === "seal") {
    return (
      <SealFlow
        client={client}
        mspName="Your MSP"
        caveats={CAVEATS}
        onBack={() => withTransition(() => setRoute({ name: "hearing", clientId: client.id }))}
        onConfirm={() => {
          playSound("seal"); // the heavier press
          withTransition(() => {
            dispatch({ type: "seal", clientId: client.id, sealedAt: new Date().toISOString() });
            setRoute({ name: "board" });
          });
        }}
      />
    );
  }

  return (
    <Hearing
      client={client}
      soundPersistent={persistent}
      onVerdict={(user: string, verdict: Verdict) => {
        playSound("stamp"); // the verdict lands
        // the docket counter advances to the next case — the tick
        if (casesRemaining(client) > 1) playSound("tick");
        withTransition(() =>
          dispatch({ type: "hear", clientId: client.id, user, verdict }),
        );
      }}
      onAcceptAllSuggested={() => {
        playSound("shuffle"); // the whole stack moves at once
        withTransition(() =>
          dispatch({ type: "accept-all-suggested", clientId: client.id }),
        );
      }}
      onRequestSeal={() => {
        // double gate: the button is disabled AND the route refuses
        if (casesRemaining(client) === 0) {
          withTransition(() => setRoute({ name: "seal", clientId: client.id }));
        }
      }}
    />
  );
}
